"""Security headers, rate limiting, request size guard."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        settings = get_settings()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["X-SEO-Autopilot"] = "1"
        response.headers["Cache-Control"] = "no-store"
        # CSP for API JSON – restrictive default
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding window. Stricter on auth endpoints."""

    def __init__(
        self,
        app,
        max_requests: int = 120,
        window_seconds: int = 60,
        auth_max_requests: int = 20,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.auth_max = auth_max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window
        key = f"{ip}:{path.split('?')[0]}"
        # Global IP bucket
        global_key = f"ip:{ip}"
        hits = [t for t in self._hits[global_key] if t >= window_start]
        limit = self.auth_max if path.startswith("/api/auth") else self.max_requests
        # Auth also uses path-specific tighter limit
        if path.startswith("/api/auth"):
            path_hits = [t for t in self._hits[key] if t >= window_start]
            if len(path_hits) >= self.auth_max:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many auth attempts. Try again later."},
                    headers={"Retry-After": str(self.window)},
                )
            path_hits.append(now)
            self._hits[key] = path_hits

        if len(hits) >= limit * 3:  # overall IP ceiling
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
                headers={"Retry-After": str(self.window)},
            )
        hits.append(now)
        self._hits[global_key] = hits
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized bodies early (default 1 MB)."""

    def __init__(self, app, max_body_bytes: int = 1_048_576):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cl = request.headers.get("content-length")
        if cl:
            try:
                if int(cl) > self.max_body_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        return await call_next(request)
