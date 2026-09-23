"""Authentication – httpOnly cookies (primary) + token in body for API clients."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify

from app.api.schemas import Token, UserCreate, UserLogin, UserOut
from app.database.session import get_db
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.models.audit_log import AuditLog
from app.security.auth import (
    create_access_token,
    get_current_user,
    cookie_params,
)
from app.security.password import hash_password, verify_password, validate_password_strength

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.client.host if request.client else None


def _set_auth_cookie(response: Response, token: str) -> None:
    params = cookie_params()
    response.set_cookie(
        key=params["key"],
        value=token,
        httponly=True,
        secure=params["secure"],
        samesite=params["samesite"],
        max_age=params["max_age"],
        path=params["path"],
    )


def _clear_auth_cookie(response: Response) -> None:
    params = cookie_params()
    response.delete_cookie(key=params["key"], path=params["path"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_password_strength(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        full_name=(payload.full_name or "").strip()[:255] or None,
    )
    db.add(user)
    await db.flush()

    base_slug = slugify(payload.full_name or payload.email.split("@")[0]) or "org"
    slug = base_slug
    counter = 1
    while True:
        exists = await db.execute(select(Organization).where(Organization.slug == slug))
        if not exists.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
        if counter > 1000:
            raise HTTPException(status_code=500, detail="Could not allocate organization")

    org = Organization(
        name=payload.full_name or f"{payload.email.split('@')[0]}'s Workspace",
        slug=slug,
    )
    db.add(org)
    await db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
    db.add(
        AuditLog(
            user_id=user.id,
            organization_id=org.id,
            action="auth.register",
            resource_type="user",
            resource_id=user.id,
            ip_address=_client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:500],
        )
    )
    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.id)
    _set_auth_cookie(response, token)
    # access_token still returned for non-browser API clients; browsers should rely on cookie
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        db.add(
            AuditLog(
                user_id=user.id if user else None,
                action="auth.login_failed",
                resource_type="user",
                details={"email": payload.email.lower()[:320]},
                ip_address=_client_ip(request),
                user_agent=(request.headers.get("user-agent") or "")[:500],
            )
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    db.add(
        AuditLog(
            user_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=user.id,
            ip_address=_client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:500],
        )
    )
    await db.commit()

    token = create_access_token(subject=user.id)
    _set_auth_cookie(response, token)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Clear httpOnly session cookie. Safe to call when not logged in."""
    _clear_auth_cookie(response)
    return {"ok": True, "message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
