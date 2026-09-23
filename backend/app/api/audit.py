"""Audit log listing (admin / compliance)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.audit_log import AuditLog
from app.models.organization import OrganizationMember
from app.models.user import User
from app.security.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/logs", response_model=list[AuditOut])
async def list_audit_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Org members can see their own + org-related; superuser sees all
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 200))
    if not current_user.is_superuser:
        q = q.where(AuditLog.user_id == current_user.id)
    rows = (await db.execute(q)).scalars().all()
    return rows
