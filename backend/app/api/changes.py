"""SEO change proposals – list, approve, reject, mark applied."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.change import Change
from app.models.organization import OrganizationMember
from app.models.user import User
from app.models.website import Website
from app.models.audit_log import AuditLog
from app.security.auth import get_current_user

router = APIRouter(prefix="/websites", tags=["Changes"])


class ChangeOut(BaseModel):
    id: str
    website_id: str
    change_type: str
    description: str
    before: Optional[dict] = None
    after: Optional[dict] = None
    status: str
    applied_via: Optional[str] = None
    created_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChangeStatusIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected|applied|rolled_back)$")
    applied_via: Optional[str] = None
    note: Optional[str] = None


async def _website_for_user(db: AsyncSession, website_id: str, user: User) -> Website:
    org_ids = (
        await db.execute(
            select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id)
        )
    ).scalars().all()
    website = (
        await db.execute(
            select(Website).where(Website.id == website_id, Website.organization_id.in_(list(org_ids)))
        )
    ).scalar_one_or_none()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


@router.get("/{website_id}/changes", response_model=list[ChangeOut])
async def list_changes(
    website_id: str,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _website_for_user(db, website_id, current_user)
    q = select(Change).where(Change.website_id == website_id).order_by(Change.created_at.desc())
    if status_filter:
        q = q.where(Change.status == status_filter)
    rows = (await db.execute(q.limit(200))).scalars().all()
    return rows


@router.post("/{website_id}/changes/{change_id}/status", response_model=ChangeOut)
async def update_change_status(
    website_id: str,
    change_id: str,
    payload: ChangeStatusIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _website_for_user(db, website_id, current_user)
    change = (
        await db.execute(
            select(Change).where(Change.id == change_id, Change.website_id == website_id)
        )
    ).scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")

    change.status = payload.status
    if payload.applied_via:
        change.applied_via = payload.applied_via
    if payload.status == "applied":
        change.applied_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            user_id=current_user.id,
            action=f"change.{payload.status}",
            resource_type="change",
            resource_id=change_id,
            details={"website_id": website_id, "note": payload.note, "change_type": change.change_type},
        )
    )
    await db.commit()
    await db.refresh(change)
    return change


@router.post("/{website_id}/changes/seed-from-recommendations")
async def seed_changes_from_recommendations(
    website_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create proposed Change rows from open recommendations (approval queue)."""
    from app.models.recommendation import Recommendation

    await _website_for_user(db, website_id, current_user)
    recs = (
        await db.execute(
            select(Recommendation)
            .where(Recommendation.website_id == website_id, Recommendation.status.in_(["pending", "open", "approved"]))
            .limit(50)
        )
    ).scalars().all()
    created = 0
    for r in recs:
        existing = (
            await db.execute(
                select(Change).where(
                    Change.website_id == website_id,
                    Change.recommendation_id == r.id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        db.add(
            Change(
                website_id=website_id,
                recommendation_id=r.id,
                change_type=r.category or "recommendation",
                description=r.title or r.what or "SEO recommendation",
                after={"how": r.how, "impact": r.impact, "effort": r.effort},
                status="proposed" if r.requires_approval else "approved",
            )
        )
        created += 1
    await db.commit()
    return {"created": created, "message": "Proposed changes seeded for approval workflow"}
