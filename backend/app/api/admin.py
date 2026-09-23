"""Admin / organization settings API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db
from app.models.organization import Organization, OrganizationMember
from app.models.settings import OrganizationSettings, SystemSetting
from app.models.user import User
from app.models.website import Website
from app.models.crawl import CrawlRun
from app.security.auth import get_current_user, require_superuser

router = APIRouter(prefix="/admin", tags=["Admin"])
app_settings = get_settings()


# ── Schemas ───────────────────────────────────────────────────────────────────

class OrgSettingsOut(BaseModel):
    organization_id: str
    default_max_pages: int
    default_max_depth: int
    default_crawl_delay: float
    ai_provider: str
    ai_api_key_set: bool
    github_enabled: bool
    netlify_enabled: bool
    vercel_enabled: bool
    gsc_enabled: bool
    ga4_enabled: bool
    wordpress_enabled: bool
    auto_optimize_default: bool
    require_approval_default: bool
    max_websites_override: Optional[int] = None
    company_name: Optional[str] = None
    report_footer: Optional[str] = None
    alert_email: Optional[str] = None
    notify_on_crawl_complete: bool
    notify_on_score_drop: bool
    score_drop_threshold: int
    extra: Optional[dict] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrgSettingsUpdate(BaseModel):
    default_max_pages: Optional[int] = Field(None, ge=1, le=500)
    default_max_depth: Optional[int] = Field(None, ge=1, le=10)
    default_crawl_delay: Optional[float] = Field(None, ge=0, le=10)
    ai_provider: Optional[str] = Field(None, pattern="^(rules|openai|anthropic|gemini|local)$")
    ai_api_key: Optional[str] = None  # write-only
    github_enabled: Optional[bool] = None
    netlify_enabled: Optional[bool] = None
    vercel_enabled: Optional[bool] = None
    gsc_enabled: Optional[bool] = None
    ga4_enabled: Optional[bool] = None
    wordpress_enabled: Optional[bool] = None
    auto_optimize_default: Optional[bool] = None
    require_approval_default: Optional[bool] = None
    max_websites_override: Optional[int] = Field(None, ge=1, le=1000)
    company_name: Optional[str] = Field(None, max_length=255)
    report_footer: Optional[str] = None
    alert_email: Optional[EmailStr] = None
    notify_on_crawl_complete: Optional[bool] = None
    notify_on_score_drop: Optional[bool] = None
    score_drop_threshold: Optional[int] = Field(None, ge=1, le=50)
    # Integration credentials (write-only, stored in secrets)
    github_token: Optional[str] = None
    netlify_token: Optional[str] = None
    vercel_token: Optional[str] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None


class SystemInfoOut(BaseModel):
    app_name: str
    version: str
    environment: str
    database: str
    features: dict[str, bool]
    crawl_defaults: dict[str, Any]
    oauth_configured: dict[str, bool]


class DashboardStats(BaseModel):
    websites: int
    crawls: int
    organizations: int
    users_in_org: int
    plan: str
    max_websites: int


class MemberOut(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str


async def _require_org_admin(db: AsyncSession, user: User) -> tuple[str, OrganizationMember]:
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    )
    memberships = list(result.scalars().all())
    if not memberships:
        raise HTTPException(status_code=403, detail="No organization membership")
    # Prefer owner/admin
    admin = next((m for m in memberships if m.role in ("owner", "admin")), memberships[0])
    if admin.role not in ("owner", "admin") and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin role required")
    return admin.organization_id, admin


async def _get_or_create_org_settings(db: AsyncSession, org_id: str) -> OrganizationSettings:
    result = await db.execute(
        select(OrganizationSettings).where(OrganizationSettings.organization_id == org_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        s = OrganizationSettings(organization_id=org_id)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s


def _settings_out(s: OrganizationSettings) -> OrgSettingsOut:
    return OrgSettingsOut(
        organization_id=s.organization_id,
        default_max_pages=s.default_max_pages,
        default_max_depth=s.default_max_depth,
        default_crawl_delay=float(s.default_crawl_delay),
        ai_provider=s.ai_provider,
        ai_api_key_set=bool(s.ai_api_key_set or (s.secrets or {}).get("ai_api_key")),
        github_enabled=s.github_enabled,
        netlify_enabled=s.netlify_enabled,
        vercel_enabled=s.vercel_enabled,
        gsc_enabled=s.gsc_enabled,
        ga4_enabled=s.ga4_enabled,
        wordpress_enabled=s.wordpress_enabled,
        auto_optimize_default=s.auto_optimize_default,
        require_approval_default=s.require_approval_default,
        max_websites_override=s.max_websites_override,
        company_name=s.company_name,
        report_footer=s.report_footer,
        alert_email=s.alert_email,
        notify_on_crawl_complete=s.notify_on_crawl_complete,
        notify_on_score_drop=s.notify_on_score_drop,
        score_drop_threshold=s.score_drop_threshold,
        extra=s.extra,
        updated_at=s.updated_at,
    )


@router.get("/settings", response_model=OrgSettingsOut)
async def get_org_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, _ = await _require_org_admin(db, current_user)
    s = await _get_or_create_org_settings(db, org_id)
    return _settings_out(s)


@router.put("/settings", response_model=OrgSettingsOut)
async def update_org_settings(
    payload: OrgSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, _ = await _require_org_admin(db, current_user)
    s = await _get_or_create_org_settings(db, org_id)

    data = payload.model_dump(exclude_unset=True)
    secrets = dict(s.secrets or {})

    # Write-only secret fields
    if "ai_api_key" in data:
        key = data.pop("ai_api_key")
        if key:
            secrets["ai_api_key"] = key
            s.ai_api_key_set = True
        elif key == "":
            secrets.pop("ai_api_key", None)
            s.ai_api_key_set = False

    for secret_field in ("github_token", "netlify_token", "vercel_token", "google_client_id", "google_client_secret"):
        if secret_field in data:
            val = data.pop(secret_field)
            if val:
                secrets[secret_field] = val
            elif val == "":
                secrets.pop(secret_field, None)

    for k, v in data.items():
        if hasattr(s, k) and v is not None:
            setattr(s, k, v)

    s.secrets = secrets
    await db.commit()
    await db.refresh(s)
    return _settings_out(s)


@router.get("/system", response_model=SystemInfoOut)
async def system_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_admin(db, current_user)
    return SystemInfoOut(
        app_name=app_settings.app_name,
        version="0.1.0",
        environment=app_settings.app_env,
        database="sqlite" if "sqlite" in app_settings.database_url else "postgresql",
        features={
            "crawler": True,
            "technical_seo": True,
            "keywords": True,
            "schema": True,
            "content": True,
            "autofix": True,
            "reports": True,
            "monitoring": True,
            "github": True,
            "netlify": True,
            "vercel": True,
            "gsc": True,
            "ga4": True,
            "wordpress": False,
        },
        crawl_defaults={
            "max_pages": app_settings.max_pages_per_crawl,
            "max_depth": app_settings.max_crawl_depth,
            "delay": app_settings.crawl_delay_seconds,
            "user_agent": app_settings.user_agent,
        },
        oauth_configured={
            "github": bool(app_settings.github_client_id and app_settings.github_client_secret),
            "google": bool(app_settings.google_client_id and app_settings.google_client_secret),
        },
    )


@router.get("/stats", response_model=DashboardStats)
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, _ = await _require_org_admin(db, current_user)
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()

    websites = (
        await db.execute(
            select(func.count()).select_from(Website).where(Website.organization_id == org_id)
        )
    ).scalar() or 0

    site_ids = (
        await db.execute(select(Website.id).where(Website.organization_id == org_id))
    ).scalars().all()
    crawls = 0
    if site_ids:
        crawls = (
            await db.execute(
                select(func.count()).select_from(CrawlRun).where(CrawlRun.website_id.in_(list(site_ids)))
            )
        ).scalar() or 0

    members = (
        await db.execute(
            select(func.count()).select_from(OrganizationMember).where(
                OrganizationMember.organization_id == org_id
            )
        )
    ).scalar() or 0

    return DashboardStats(
        websites=websites,
        crawls=crawls,
        organizations=1,
        users_in_org=members,
        plan=org.plan,
        max_websites=org.max_websites,
    )


@router.get("/members", response_model=list[MemberOut])
async def list_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, _ = await _require_org_admin(db, current_user)
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == org_id)
    )
    out = []
    for member, user in result.all():
        out.append(
            MemberOut(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=member.role,
            )
        )
    return out


@router.get("/system-settings")
async def list_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Platform-level key/value settings (admin). Secrets never returned."""
    if not current_user.is_superuser:
        # org admins can read non-secret keys
        await _require_org_admin(db, current_user)
    result = await db.execute(select(SystemSetting))
    rows = result.scalars().all()
    return [
        {"key": r.key, "value": r.value, "description": r.description, "updated_at": r.updated_at}
        for r in rows
    ]


class SystemSettingIn(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: dict
    description: Optional[str] = None


@router.put("/system-settings")
async def upsert_system_setting(
    payload: SystemSettingIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    # Block obvious secret keys from being stored as plain system settings via this path
    blocked = {"openai_api_key", "anthropic_api_key", "secret_key", "database_url"}
    if payload.key.lower() in blocked:
        raise HTTPException(status_code=400, detail="Use organization secrets for API keys")

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == payload.key))
    row = result.scalar_one_or_none()
    if not row:
        row = SystemSetting(key=payload.key)
        db.add(row)
    row.value = payload.value
    row.description = payload.description
    await db.commit()
    return {"key": row.key, "value": row.value, "description": row.description}
