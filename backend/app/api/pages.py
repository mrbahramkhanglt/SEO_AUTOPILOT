"""Discovered pages listing."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.crawl import Page
from app.models.organization import OrganizationMember
from app.models.user import User
from app.models.website import Website
from app.security.auth import get_current_user

router = APIRouter(prefix="/websites", tags=["Pages"])


class PageOut(BaseModel):
    id: str
    url: str
    status_code: Optional[int] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: Optional[str] = None
    word_count: Optional[int] = None
    is_indexable: bool
    has_structured_data: bool
    is_thin_content: bool
    depth: int
    crawled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/{website_id}/pages", response_model=list[PageOut])
async def list_pages(
    website_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_ids = (
        await db.execute(
            select(OrganizationMember.organization_id).where(
                OrganizationMember.user_id == current_user.id
            )
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

    result = await db.execute(
        select(Page)
        .where(Page.website_id == website_id)
        .order_by(Page.crawled_at.desc().nullslast())
        .limit(limit)
    )
    return [PageOut.model_validate(p) for p in result.scalars().all()]
