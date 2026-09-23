"""JWT authentication – Bearer header OR httpOnly cookie."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db
from app.models.user import User

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    getattr(settings, "access_token_expire_minutes", 60 * 24)
)


def create_access_token(subject: str, extra: Optional[dict[str, Any]] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "iss": settings.app_name,
        "type": "access",
    }
    if extra:
        for k in ("sub", "exp", "iat", "type"):
            extra.pop(k, None)
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        if payload.get("type") not in (None, "access"):
            raise JWTError("invalid token type")
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def extract_token(request: Request, bearer: Optional[str] = None) -> Optional[str]:
    """Prefer Authorization Bearer; fall back to httpOnly cookie."""
    if bearer:
        return bearer
    cookie_name = getattr(settings, "cookie_name", "seo_access_token")
    return request.cookies.get(cookie_name)


def cookie_params() -> dict[str, Any]:
    secure = bool(getattr(settings, "cookie_secure", False) or settings.is_production)
    samesite = (getattr(settings, "cookie_samesite", "lax") or "lax").lower()
    if samesite not in ("lax", "strict", "none"):
        samesite = "lax"
    # SameSite=None requires Secure
    if samesite == "none":
        secure = True
    return {
        "key": getattr(settings, "cookie_name", "seo_access_token"),
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "max_age": int(getattr(settings, "cookie_max_age_seconds", 60 * 60 * 24)),
        "path": "/",
    }


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    raw = extract_token(request, token)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(raw)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )
    return user


async def get_current_user_optional(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    raw = extract_token(request, token)
    if not raw:
        return None
    try:
        return await get_current_user(request=request, token=raw, db=db)
    except HTTPException:
        return None


async def require_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return current_user
