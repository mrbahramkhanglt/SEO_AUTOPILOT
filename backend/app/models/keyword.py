"""Keyword research results."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from app.database.types import JSONType as JSONB, UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("pages.id", ondelete="SET NULL"), nullable=True
    )

    keyword: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), default="primary")  # primary, secondary, long_tail
    search_intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # informational, commercial, transactional, navigational
    difficulty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_estimate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    recommended_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_h1: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_recommendations: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    website = relationship("Website", back_populates="keywords")
