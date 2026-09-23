"""SEO Autopilot AI – FastAPI application entrypoint (security-hardened)."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api import auth, websites, monitoring, pages, integrations, admin, changes, audit
from app.core.config import get_settings
from app.core.middleware import (
    SecurityHeadersMiddleware,
    SimpleRateLimitMiddleware,
    RequestSizeLimitMiddleware,
)
from app.api.schemas import Health
from app.database.session import init_db, engine

logger = logging.getLogger("seo.main")
settings = get_settings()



async def bootstrap_admin() -> None:
    """Create platform admin from ADMIN_EMAIL / ADMIN_PASSWORD env (server-side only)."""
    email = (settings.admin_email or "").strip().lower()
    password = settings.admin_password or ""
    if not email or not password:
        return
    from sqlalchemy import select
    from app.database.session import AsyncSessionLocal
    from app.models.user import User
    from app.models.organization import Organization, OrganizationMember
    from app.security.password import hash_password, validate_password_strength
    from slugify import slugify

    try:
        validate_password_strength(password)
    except ValueError as e:
        logger.error("ADMIN_PASSWORD rejected: %s", e)
        return

    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing:
            if not existing.is_superuser:
                existing.is_superuser = True
                await db.commit()
                logger.info("Admin flag set for existing user %s", email)
            return
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=settings.admin_full_name or "Platform Admin",
            is_superuser=True,
        )
        db.add(user)
        await db.flush()
        slug = slugify(settings.admin_full_name or "platform-admin") or "admin"
        org = Organization(name="Platform", slug=f"{slug}-platform")
        db.add(org)
        await db.flush()
        db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
        await db.commit()
        logger.info("Bootstrapped admin user %s (credentials from env only)", email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_production:
        if not settings.secret_key or settings.secret_key.startswith("change-me"):
            raise RuntimeError(
                "Refusing to start: set a strong SECRET_KEY in production "
                "(e.g. openssl rand -hex 32)"
            )
        if len(settings.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be at least 32 characters in production")
    await init_db()
    logger.info("Database ready (%s)", settings.database_url.split("://")[0])
    await bootstrap_admin()
    yield
    await engine.dispose()


_docs = None if (settings.is_production and settings.disable_docs_in_production) else "/docs"
_redoc = None if (settings.is_production and settings.disable_docs_in_production) else "/redoc"
_openapi = None if (settings.is_production and settings.disable_docs_in_production) else "/openapi.json"

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Autonomous AI SEO Operating System. "
        "Enter a website URL → crawl, audit, analyze, optimize, monitor."
    ),
    lifespan=lifespan,
    docs_url=_docs,
    redoc_url=_redoc,
    openapi_url=_openapi,
)

# Middleware order: last added = outermost on request
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)
app.add_middleware(
    SimpleRateLimitMiddleware,
    max_requests=max(60, settings.rate_limit_per_minute),
    window_seconds=60,
    auth_max_requests=15,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
# Trusted hosts (skip strict list in development)
if settings.is_production and settings.allowed_hosts_list:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list + ["localhost", "127.0.0.1"],
    )

app.include_router(auth.router, prefix="/api")
app.include_router(websites.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(pages.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(changes.router, prefix="/api")
app.include_router(audit.router, prefix="/api")


def _safe_detail(detail: object) -> object:
    """Avoid leaking internal exception strings in production."""
    if not settings.is_production:
        return detail
    if isinstance(detail, str) and any(
        x in detail.lower() for x in ("traceback", "sqlalchemy", "file \"/", "operationalerror")
    ):
        return "Internal server error"
    return detail


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": _safe_detail(exc.detail)},
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Do not echo full body; return structured validation errors only
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=Health, tags=["System"])
async def health():
    db_ok = True
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return Health(
        status="ok" if db_ok else "degraded",
        version=__version__,
        environment=settings.app_env,
    )


@app.get("/live", tags=["System"])
async def live():
    """Kubernetes-style liveness: process is up."""
    return {"status": "alive"}


@app.get("/ready", tags=["System"])
async def ready():
    """Kubernetes-style readiness: DB reachable."""
    from sqlalchemy import text
    from fastapi.responses import JSONResponse, PlainTextResponse

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


@app.get("/", tags=["System"])
async def root():
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": _docs,
        "message": "SEO Autopilot AI is running. Provide a website URL to begin.",
    }


@app.get("/robots.txt", tags=["System"])
async def robots_txt():
    body = "User-agent: *\nDisallow: /api/\nDisallow: /docs\nDisallow: /redoc\n"
    return PlainTextResponse(body)
