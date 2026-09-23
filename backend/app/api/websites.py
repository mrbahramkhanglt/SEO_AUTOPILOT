from app.core.redis_cache import cache_get, cache_set, cache_delete
import io
import zipfile
"""Website onboarding and management endpoints."""
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    CrawlRunOut,
    CrawlStart,
    KeywordOut,
    Message,
    RecommendationOut,
    ReportListItem,
    ReportOut,
    SEOIssueOut,
    SEOScoreOut,
    WebsiteCreate,
    WebsiteList,
    WebsiteOut,
)
from app.database.session import get_db
from app.models.crawl import CrawlRun
from app.models.organization import Organization, OrganizationMember
from app.models.seo import SEOIssue, SEOScore
from app.models.keyword import Keyword
from app.models.recommendation import Recommendation
from app.models.report import Report
from app.models.user import User
from app.models.website import Website
from app.security.auth import get_current_user
from app.security.ssrf import SSRFError, validate_url_for_crawl
from app.services.website_service import validate_and_discover_website
from app.services.orchestrator import run_full_pipeline
import asyncio

router = APIRouter(prefix="/websites", tags=["Websites"])


async def _get_user_org_ids(db: AsyncSession, user_id: str) -> list[str]:
    result = await db.execute(
        select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user_id)
    )
    return list(result.scalars().all())


async def _get_website_for_user(
    db: AsyncSession, website_id: str, user: User
) -> Website:
    org_ids = await _get_user_org_ids(db, user.id)
    result = await db.execute(
        select(Website).where(Website.id == website_id, Website.organization_id.in_(org_ids))
    )
    website = result.scalar_one_or_none()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


@router.post("", response_model=WebsiteOut, status_code=status.HTTP_201_CREATED)
async def create_website(
    payload: WebsiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Onboard a new website by URL. Minimum workflow requires only a URL."""
    # SSRF + basic validation
    try:
        safe_url = validate_url_for_crawl(payload.url)
    except SSRFError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    parsed = urlparse(safe_url)
    domain = parsed.hostname or ""

    # Resolve organization
    org_ids = await _get_user_org_ids(db, current_user.id)
    if not org_ids:
        raise HTTPException(status_code=400, detail="No organization found. Please re-register.")

    org_id = payload.organization_id or org_ids[0]
    if org_id not in org_ids:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    # Plan limits
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one()
    count_result = await db.execute(
        select(func.count()).select_from(Website).where(Website.organization_id == org_id)
    )
    current_count = count_result.scalar() or 0
    if current_count >= org.max_websites:
        raise HTTPException(
            status_code=403,
            detail=f"Plan limit reached ({org.max_websites} websites). Upgrade to add more.",
        )

    # Create website record
    website = Website(
        organization_id=org_id,
        url=safe_url,
        domain=domain,
        name=payload.name or domain,
        status="validating",
    )
    db.add(website)
    await db.flush()

    # Quick discovery (robots, sitemap, tech stack) – non-blocking for MVP
    try:
        discovery = await validate_and_discover_website(safe_url)
        website.is_valid = discovery.get("is_valid", False)
        website.validation_error = discovery.get("error")
        website.has_robots = discovery.get("has_robots", False)
        website.has_sitemap = discovery.get("has_sitemap", False)
        website.robots_url = discovery.get("robots_url")
        website.sitemap_url = discovery.get("sitemap_url")
        website.technology_stack = discovery.get("technology_stack")
        website.status = "ready" if website.is_valid else "error"
    except Exception as e:
        website.is_valid = False
        website.validation_error = str(e)
        website.status = "error"

    await db.commit()
    await db.refresh(website)
    return WebsiteOut.model_validate(website)


@router.get("", response_model=WebsiteList)
async def list_websites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_ids = await _get_user_org_ids(db, current_user.id)
    result = await db.execute(
        select(Website)
        .where(Website.organization_id.in_(org_ids))
        .order_by(Website.created_at.desc())
    )
    items = result.scalars().all()
    return WebsiteList(items=[WebsiteOut.model_validate(w) for w in items], total=len(items))


@router.get("/{website_id}", response_model=WebsiteOut)
async def get_website(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    website = await _get_website_for_user(db, website_id, current_user)
    return WebsiteOut.model_validate(website)


@router.post("/{website_id}/crawl", response_model=CrawlRunOut, status_code=status.HTTP_202_ACCEPTED)
async def start_crawl(
    website_id: str,
    payload: CrawlStart = CrawlStart(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a full SEO crawl + analysis pipeline (async)."""
    website = await _get_website_for_user(db, website_id, current_user)
    if not website.is_valid:
        raise HTTPException(status_code=400, detail="Website is not valid. Fix validation errors first.")

    # Create crawl run
    crawl = CrawlRun(
        website_id=website.id,
        status="pending",
        progress=0,
        current_step="Queued",
        message="Crawl queued",
        config={
            "max_pages": payload.max_pages or website.max_pages,
            "max_depth": payload.max_depth or website.crawl_depth,
        },
    )
    db.add(crawl)
    website.status = "crawling"
    await db.commit()
    await db.refresh(crawl)

    # Run pipeline in background (in-process for MVP; Celery in production)
    async def _bg():
        from app.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await run_full_pipeline(session, website.id, crawl.id)

    asyncio.create_task(_bg())

    return CrawlRunOut.model_validate(crawl)


@router.get("/{website_id}/crawls", response_model=list[CrawlRunOut])
async def list_crawls(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(CrawlRun)
        .where(CrawlRun.website_id == website_id)
        .order_by(CrawlRun.created_at.desc())
        .limit(50)
    )
    return [CrawlRunOut.model_validate(c) for c in result.scalars().all()]


@router.get("/{website_id}/seo-score", response_model=SEOScoreOut | None)
async def get_seo_score(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)

    cache_key = f"seo:v1:score:{website_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = await db.execute(
        select(SEOScore)
        .where(SEOScore.website_id == website_id)
        .order_by(SEOScore.created_at.desc())
        .limit(1)
    )
    score = result.scalar_one_or_none()
    if not score:
        return None
    out = SEOScoreOut.model_validate(score)
    await cache_set(cache_key, out.model_dump(mode="json"), ttl=600)
    return out


@router.get("/{website_id}/issues", response_model=list[SEOIssueOut])
async def list_issues(
    website_id: str,
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)
    q = select(SEOIssue).where(SEOIssue.website_id == website_id)
    if severity:
        q = q.where(SEOIssue.severity == severity)
    q = q.order_by(SEOIssue.priority_score.desc().nullslast(), SEOIssue.created_at.desc())
    result = await db.execute(q.limit(200))
    return [SEOIssueOut.model_validate(i) for i in result.scalars().all()]




@router.get("/{website_id}/keywords", response_model=list[KeywordOut])
async def list_keywords(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Keyword)
        .where(Keyword.website_id == website_id)
        .order_by(Keyword.created_at.desc())
        .limit(300)
    )
    return [KeywordOut.model_validate(k) for k in result.scalars().all()]


@router.get("/{website_id}/recommendations", response_model=list[RecommendationOut])
async def list_recommendations(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.website_id == website_id)
        .order_by(Recommendation.priority.desc())
        .limit(200)
    )
    return [RecommendationOut.model_validate(r) for r in result.scalars().all()]




@router.get("/{website_id}/reports", response_model=list[ReportListItem])
async def list_reports(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Report)
        .where(Report.website_id == website_id)
        .order_by(Report.created_at.desc())
        .limit(20)
    )
    return [ReportListItem.model_validate(r) for r in result.scalars().all()]


@router.get("/{website_id}/reports/latest", response_model=ReportOut | None)
async def latest_report(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Report)
        .where(Report.website_id == website_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        return None
    return ReportOut.model_validate(report)


@router.get("/{website_id}/reports/{report_id}", response_model=ReportOut)
async def get_report(
    website_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.website_id == website_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportOut.model_validate(report)


@router.get("/{website_id}/autofix")
async def get_autofix(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return latest auto-fix artifacts from the most recent report."""
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Report)
        .where(Report.website_id == website_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report or not report.content:
        return {"message": "No autofix available. Run a crawl first.", "autofix": None}
    autofix = (report.content or {}).get("autofix")
    return {"autofix": autofix, "report_id": report.id}





@router.get("/{website_id}/autofix.zip")
async def download_autofix_zip(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download robots, sitemap, metadata, and schema as a ZIP."""
    import json
    from app.models.report import Report
    await _get_website_for_user(db, website_id, current_user)
    report = (
        await db.execute(
            select(Report).where(Report.website_id == website_id).order_by(Report.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if not report or not report.content:
        raise HTTPException(status_code=404, detail="No autofix available. Run a crawl first.")
    af = (report.content or {}).get("autofix") or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if af.get("robots_txt"):
            zf.writestr("robots.txt", af["robots_txt"])
        if af.get("sitemap_xml"):
            zf.writestr("sitemap.xml", af["sitemap_xml"])
        if af.get("metadata_fixes"):
            zf.writestr("metadata-fixes.json", json.dumps(af["metadata_fixes"], indent=2, ensure_ascii=False))
        if af.get("schema_blocks"):
            zf.writestr("schema-blocks.json", json.dumps(af["schema_blocks"], indent=2, ensure_ascii=False))
        if af.get("internal_link_suggestions"):
            zf.writestr("internal-links.json", json.dumps(af["internal_link_suggestions"], indent=2, ensure_ascii=False))
        zf.writestr(
            "README.txt",
            "SEO Autopilot auto-fix package.\n"
            "Potential SEO improvement only — rankings are never guaranteed.\n"
            "Review files before deploying to production.\n",
        )
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="seo-autofix-{website_id[:8]}.zip"'},
    )


@router.get("/{website_id}/reports/latest/export.md")
async def export_report_markdown(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.report import Report
    from app.seo.export import report_to_markdown
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Report).where(Report.website_id == website_id).order_by(Report.created_at.desc()).limit(1)
    )
    report = result.scalar_one_or_none()
    if not report or not report.content:
        raise HTTPException(status_code=404, detail="No report available")
    md = report_to_markdown(report.content)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="seo-report-{website_id[:8]}.md"'},
    )


@router.get("/{website_id}/reports/latest/export.html")
async def export_report_html(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.report import Report
    from app.seo.export import report_to_html
    await _get_website_for_user(db, website_id, current_user)
    result = await db.execute(
        select(Report).where(Report.website_id == website_id).order_by(Report.created_at.desc()).limit(1)
    )
    report = result.scalar_one_or_none()
    if not report or not report.content:
        raise HTTPException(status_code=404, detail="No report available")
    html = report_to_html(report.content)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="seo-report-{website_id[:8]}.html"'},
    )


@router.delete("/{website_id}", response_model=Message)
async def delete_website(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    website = await _get_website_for_user(db, website_id, current_user)
    await db.delete(website)
    await db.commit()
    return Message(message="Website deleted")
