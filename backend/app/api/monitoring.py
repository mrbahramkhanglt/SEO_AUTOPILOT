"""Monitoring schedule and before/after comparison endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.organization import OrganizationMember
from app.models.schedule import MonitorSchedule
from app.models.user import User
from app.models.website import Website
from app.security.auth import get_current_user
from app.services.monitoring import compare_scores, upsert_schedule

router = APIRouter(prefix="/websites", tags=["Monitoring"])


class ScheduleIn(BaseModel):
    frequency: str = Field(default="weekly", pattern="^(daily|weekly|monthly)$")
    is_active: bool = True
    auto_optimize: bool = False
    preferred_hour_utc: int = Field(default=3, ge=0, le=23)


class ScheduleOut(BaseModel):
    id: str
    website_id: str
    frequency: str
    is_active: bool
    auto_optimize: bool
    preferred_hour_utc: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


async def _get_website(db: AsyncSession, website_id: str, user: User) -> Website:
    org_ids = (
        await db.execute(
            select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id)
        )
    ).scalars().all()
    result = await db.execute(
        select(Website).where(Website.id == website_id, Website.organization_id.in_(list(org_ids)))
    )
    website = result.scalar_one_or_none()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


@router.put("/{website_id}/schedule", response_model=ScheduleOut)
async def set_schedule(
    website_id: str,
    payload: ScheduleIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website(db, website_id, current_user)
    sched = await upsert_schedule(
        db,
        website_id,
        frequency=payload.frequency,
        is_active=payload.is_active,
        auto_optimize=payload.auto_optimize,
        preferred_hour_utc=payload.preferred_hour_utc,
    )
    return ScheduleOut.model_validate(sched)


@router.get("/{website_id}/schedule", response_model=ScheduleOut | None)
async def get_schedule(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website(db, website_id, current_user)
    result = await db.execute(
        select(MonitorSchedule).where(MonitorSchedule.website_id == website_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        return None
    return ScheduleOut.model_validate(sched)


@router.get("/{website_id}/compare")
async def score_comparison(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_website(db, website_id, current_user)
    return await compare_scores(db, website_id)
