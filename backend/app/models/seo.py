"""SEO Score and Issues."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from app.database.types import JSONType as JSONB, UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class SEOScore(Base):
    __tablename__ = "seo_scores"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crawl_run_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("crawl_runs.id", ondelete="SET NULL"), nullable=True
    )

    overall: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100

    technical: Mapped[int] = mapped_column(Integer, default=0)
    on_page: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[int] = mapped_column(Integer, default=0)
    performance: Mapped[int] = mapped_column(Integer, default=0)
    indexability: Mapped[int] = mapped_column(Integer, default=0)
    structured_data: Mapped[int] = mapped_column(Integer, default=0)
    internal_linking: Mapped[int] = mapped_column(Integer, default=0)
    mobile: Mapped[int] = mapped_column(Integer, default=0)
    accessibility: Mapped[int] = mapped_column(Integer, default=0)
    authority: Mapped[int] = mapped_column(Integer, default=0)

    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    website = relationship("Website", back_populates="scores")


class SEOIssue(Base):
    __tablename__ = "seo_issues"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("pages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    crawl_run_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("crawl_runs.id", ondelete="SET NULL"), nullable=True
    )

    category: Mapped[str] = mapped_column(String(100), nullable=False)  # technical, on_page, content, ...
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g. MISSING_META_DESCRIPTION
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, high, medium, low

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_impact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # high, medium, low
    effort: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # easy, medium, hard
    priority_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="open", nullable=False
    )  # open, fixed, ignored, in_progress

    # Extra data (current value, suggested value, etc.)
    data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    website = relationship("Website", back_populates="issues")
