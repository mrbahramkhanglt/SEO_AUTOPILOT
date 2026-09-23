"""Monitoring schedule model."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import UUIDType as UUID, JSONType as JSONB


class MonitorSchedule(Base):
    __tablename__ = "monitor_schedules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    website_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # daily | weekly | monthly
    frequency: Mapped[str] = mapped_column(String(20), default="weekly", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_optimize: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # HH:MM UTC preferred run window
    preferred_hour_utc: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
