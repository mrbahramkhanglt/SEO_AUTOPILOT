"""Third-party integration endpoints (GitHub, Netlify, Vercel, GSC, GA4)."""
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db
from app.integrations.github import GitHubIntegration
from app.integrations.netlify import NetlifyIntegration
from app.integrations.vercel import VercelIntegration
from app.integrations.gsc import GSCIntegration
from app.integrations.ga4 import GA4Integration
from app.integrations.wordpress import WordPressIntegration, WPGraphQLClient
from app.models.integration import Integration
from app.models.organization import OrganizationMember
from app.models.report import Report
from app.models.user import User
from app.models.website import Website
from app.security.auth import get_current_user

router = APIRouter(prefix="/integrations", tags=["Integrations"])
settings = get_settings()


class StatusOut(BaseModel):
    provider: str
    configured: bool
    authorize_url: Optional[str] = None
    message: str


class GitHubApplyIn(BaseModel):
    website_id: str
    owner: str
    repo: str
    base_branch: str = "main"
    access_token: str


class TokenIn(BaseModel):
    access_token: str
    team_id: Optional[str] = None


class NetlifyDeployIn(BaseModel):
    site_id: str
    access_token: str
    clear_cache: bool = False


class GSCAnalyticsIn(BaseModel):
    access_token: str
    site_url: str
    start_date: str = Field(description="YYYY-MM-DD")
    end_date: str = Field(description="YYYY-MM-DD")


class GA4ReportIn(BaseModel):
    access_token: str
    property_id: str
    start_date: str = "28daysAgo"
    end_date: str = "yesterday"


async def _user_website(db: AsyncSession, website_id: str, user: User) -> Website:
    org_ids = (
        await db.execute(
            select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id)
        )
    ).scalars().all()
    website = (
        await db.execute(
            select(Website).where(
                Website.id == website_id, Website.organization_id.in_(list(org_ids))
            )
        )
    ).scalar_one_or_none()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


# ── GitHub ────────────────────────────────────────────────────────────────────

@router.get("/github/status", response_model=StatusOut)
async def github_status(current_user: User = Depends(get_current_user)):
    gh = GitHubIntegration()
    if not gh.is_configured():
        return StatusOut(
            provider="github",
            configured=False,
            message="Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to enable OAuth.",
        )
    redirect = f"{settings.api_url}/api/integrations/github/callback"
    url = gh.authorize_url(state=str(uuid4()), redirect_uri=redirect)
    return StatusOut(provider="github", configured=True, authorize_url=url, message="OAuth ready")


@router.post("/github/apply")
async def github_apply_seo(
    payload: GitHubApplyIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    website = await _user_website(db, payload.website_id, current_user)
    report = (
        await db.execute(
            select(Report)
            .where(Report.website_id == website.id)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not report or not report.content:
        raise HTTPException(status_code=400, detail="No SEO report/autofix. Run a crawl first.")

    autofix = (report.content or {}).get("autofix") or {}
    gh = GitHubIntegration(access_token=payload.access_token)
    files = gh.build_seo_files_from_autofix(autofix)
    if not files:
        raise HTTPException(status_code=400, detail="No autofix files to commit")

    try:
        branch_info = await gh.create_seo_branch(payload.owner, payload.repo, payload.base_branch)
        branch = branch_info["branch"]
        commit = await gh.commit_files(payload.owner, payload.repo, branch, files)
        pr = await gh.open_pull_request(
            payload.owner,
            payload.repo,
            head_branch=branch,
            base_branch=branch_info.get("base") or payload.base_branch,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub error: {e}") from e

    db.add(
        Integration(
            website_id=website.id,
            provider="github",
            status="connected",
            external_name=f"{payload.owner}/{payload.repo}",
            metadata_={"last_branch": branch, "last_pr": pr},
        )
    )
    await db.commit()
    return {
        "branch": branch,
        "commit": commit,
        "pull_request": pr,
        "files": list(files.keys()),
        "message": "SEO branch + PR created. Production was not modified directly.",
    }


# ── Netlify ───────────────────────────────────────────────────────────────────

@router.post("/netlify/sites")
async def netlify_sites(payload: TokenIn, current_user: User = Depends(get_current_user)):
    try:
        sites = await NetlifyIntegration(payload.access_token).list_sites()
        return {"sites": sites}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/netlify/deploy")
async def netlify_deploy(payload: NetlifyDeployIn, current_user: User = Depends(get_current_user)):
    try:
        result = await NetlifyIntegration(payload.access_token).trigger_build(
            payload.site_id, clear_cache=payload.clear_cache
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── Vercel ────────────────────────────────────────────────────────────────────

@router.post("/vercel/projects")
async def vercel_projects(payload: TokenIn, current_user: User = Depends(get_current_user)):
    try:
        projects = await VercelIntegration(payload.access_token, payload.team_id).list_projects()
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/vercel/deployments")
async def vercel_deployments(
    project_id: str,
    payload: TokenIn,
    current_user: User = Depends(get_current_user),
):
    try:
        deps = await VercelIntegration(payload.access_token, payload.team_id).list_deployments(project_id)
        return {"deployments": deps}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── Google Search Console ─────────────────────────────────────────────────────

@router.get("/gsc/status", response_model=StatusOut)
async def gsc_status(current_user: User = Depends(get_current_user)):
    gsc = GSCIntegration()
    if not gsc.is_configured():
        return StatusOut(
            provider="gsc",
            configured=False,
            message="Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET for GSC OAuth.",
        )
    redirect = f"{settings.api_url}/api/integrations/gsc/callback"
    return StatusOut(
        provider="gsc",
        configured=True,
        authorize_url=gsc.authorize_url(str(uuid4()), redirect),
        message="OAuth ready",
    )


@router.post("/gsc/analytics")
async def gsc_analytics(payload: GSCAnalyticsIn, current_user: User = Depends(get_current_user)):
    try:
        data = await GSCIntegration(payload.access_token).search_analytics(
            payload.site_url, payload.start_date, payload.end_date
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── GA4 ───────────────────────────────────────────────────────────────────────

@router.get("/ga4/status", response_model=StatusOut)
async def ga4_status(current_user: User = Depends(get_current_user)):
    ga = GA4Integration()
    if not ga.is_configured():
        return StatusOut(
            provider="ga4",
            configured=False,
            message="Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET for GA4 OAuth.",
        )
    redirect = f"{settings.api_url}/api/integrations/ga4/callback"
    return StatusOut(
        provider="ga4",
        configured=True,
        authorize_url=ga.authorize_url(str(uuid4()), redirect),
        message="OAuth ready",
    )


@router.post("/ga4/report")
async def ga4_report(payload: GA4ReportIn, current_user: User = Depends(get_current_user)):
    try:
        data = await GA4Integration(payload.access_token).run_report(
            payload.property_id, payload.start_date, payload.end_date
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── WordPress ─────────────────────────────────────────────────────────────────

class WordPressConnectIn(BaseModel):
    site_url: str
    username: str
    app_password: str
    seo_plugin: str = "auto"  # auto | yoast | rankmath


class WordPressListIn(WordPressConnectIn):
    content_type: str = "pages"
    per_page: int = Field(default=20, ge=1, le=100)
    page: int = Field(default=1, ge=1)


class WordPressMetaIn(WordPressConnectIn):
    content_type: str = "pages"
    item_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    focus_kw: Optional[str] = None
    canonical: Optional[str] = None
    dry_run: bool = True
    force_overwrite: bool = False


class WPGraphQLIn(BaseModel):
    site_url: str
    username: Optional[str] = None
    app_password: Optional[str] = None
    first: int = Field(default=10, ge=1, le=50)


@router.post("/wordpress/test")
async def wordpress_test(payload: WordPressConnectIn, current_user: User = Depends(get_current_user)):
    try:
        result = await WordPressIntegration(
            payload.site_url, payload.username, payload.app_password, payload.seo_plugin
        ).test_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/wordpress/list")
async def wordpress_list(payload: WordPressListIn, current_user: User = Depends(get_current_user)):
    try:
        items = await WordPressIntegration(
            payload.site_url, payload.username, payload.app_password, payload.seo_plugin
        ).list_content(payload.content_type, payload.per_page, payload.page)
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/wordpress/meta")
async def wordpress_meta(payload: WordPressMetaIn, current_user: User = Depends(get_current_user)):
    """Preview (default) or apply SEO meta. Conflicts block apply unless force_overwrite."""
    try:
        result = await WordPressIntegration(
            payload.site_url, payload.username, payload.app_password, payload.seo_plugin
        ).apply_meta_update(
            payload.content_type,
            payload.item_id,
            title=payload.title,
            description=payload.description,
            focus_kw=payload.focus_kw,
            canonical=payload.canonical,
            dry_run=payload.dry_run,
            force_overwrite=payload.force_overwrite,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/wordpress/graphql-seo")
async def wordpress_graphql_seo(payload: WPGraphQLIn, current_user: User = Depends(get_current_user)):
    """Optional WPGraphQL read of Yoast-style seo fields."""
    try:
        data = await WPGraphQLClient(
            payload.site_url, payload.username, payload.app_password
        ).fetch_posts_seo(payload.first)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
