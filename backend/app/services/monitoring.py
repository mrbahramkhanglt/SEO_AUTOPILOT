"""Continuous monitoring – schedule crawls and compare before/after scores."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl import CrawlRun
from app.models.schedule import MonitorSchedule
from app.models.seo import SEOScore
from app.models.website import Website
from app.services.orchestrator import run_full_pipeline


def compute_next_run(frequency: str, preferred_hour: int = 3, from_dt: Optional[datetime] = None) -> datetime:
    now = from_dt or datetime.now(timezone.utc)
    base = now.replace(minute=0, second=0, microsecond=0)
    if frequency == "daily":
        nxt = base + timedelta(days=1)
    elif frequency == "monthly":
        nxt = base + timedelta(days=30)
    else:  # weekly
        nxt = base + timedelta(days=7)
    return nxt.replace(hour=preferred_hour % 24)


async def upsert_schedule(
    db: AsyncSession,
    website_id: str,
    frequency: str = "weekly",
    is_active: bool = True,
    auto_optimize: bool = False,
    preferred_hour_utc: int = 3,
) -> MonitorSchedule:
    result = await db.execute(
        select(MonitorSchedule).where(MonitorSchedule.website_id == website_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        sched = MonitorSchedule(website_id=website_id)
        db.add(sched)

    sched.frequency = frequency if frequency in ("daily", "weekly", "monthly") else "weekly"
    sched.is_active = is_active
    sched.auto_optimize = auto_optimize
    sched.preferred_hour_utc = preferred_hour_utc
    sched.next_run_at = compute_next_run(sched.frequency, preferred_hour_utc)
    await db.commit()
    await db.refresh(sched)
    return sched


async def list_due_schedules(db: AsyncSession) -> list[MonitorSchedule]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(MonitorSchedule).where(
            MonitorSchedule.is_active == True,  # noqa: E712
            MonitorSchedule.next_run_at != None,  # noqa: E711
            MonitorSchedule.next_run_at <= now,
        )
    )
    return list(result.scalars().all())


async def run_scheduled_crawl(db: AsyncSession, schedule: MonitorSchedule) -> Optional[str]:
    """Create crawl run and execute pipeline; returns crawl_run_id."""
    website = (
        await db.execute(select(Website).where(Website.id == schedule.website_id))
    ).scalar_one_or_none()
    if not website or not website.is_valid:
        schedule.last_status = "skipped"
        schedule.last_error = "Website invalid or missing"
        schedule.last_run_at = datetime.now(timezone.utc)
        schedule.next_run_at = compute_next_run(schedule.frequency, schedule.preferred_hour_utc)
        await db.commit()
        return None

    crawl = CrawlRun(
        website_id=website.id,
        status="pending",
        progress=0,
        current_step="Scheduled",
        message="Triggered by monitor schedule",
        config={
            "max_pages": website.max_pages,
            "max_depth": website.crawl_depth,
            "scheduled": True,
            "auto_optimize": schedule.auto_optimize,
        },
    )
    db.add(crawl)
    website.status = "crawling"
    await db.commit()
    await db.refresh(crawl)

    await run_full_pipeline(db, website.id, crawl.id)

    schedule.last_run_at = datetime.now(timezone.utc)
    schedule.last_status = "completed"
    schedule.last_error = None
    schedule.next_run_at = compute_next_run(schedule.frequency, schedule.preferred_hour_utc)
    await db.commit()
    return crawl.id


async def compare_scores(db: AsyncSession, website_id: str) -> dict:
    """Before/after comparison of the last two SEO scores."""
    result = await db.execute(
        select(SEOScore)
        .where(SEOScore.website_id == website_id)
        .order_by(SEOScore.created_at.desc())
        .limit(2)
    )
    scores = list(result.scalars().all())
    if not scores:
        return {"message": "No scores yet", "before": None, "after": None, "delta": None}

    after = scores[0]
    before = scores[1] if len(scores) > 1 else None

    def pack(s: SEOScore) -> dict:
        return {
            "overall": s.overall,
            "technical": s.technical,
            "on_page": s.on_page,
            "content": s.content,
            "performance": s.performance,
            "indexability": s.indexability,
            "structured_data": s.structured_data,
            "internal_linking": s.internal_linking,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }

    after_p = pack(after)
    before_p = pack(before) if before else None
    delta = None
    if before:
        delta = {
            "overall": after.overall - before.overall,
            "technical": after.technical - before.technical,
            "on_page": after.on_page - before.on_page,
            "content": after.content - before.content,
            "structured_data": after.structured_data - before.structured_data,
        }
    return {"before": before_p, "after": after_p, "delta": delta}
