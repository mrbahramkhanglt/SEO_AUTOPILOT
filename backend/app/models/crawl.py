"""Crawl runs and discovered pages."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from app.database.types import JSONType as JSONB, UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, cancelled
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    current_step: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    pages_discovered: Mapped[int] = mapped_column(Integer, default=0)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Snapshot of config used
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    website = relationship("Website", back_populates="crawl_runs")
    pages = relationship("Page", back_populates="crawl_run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CrawlRun {self.id} status={self.status}>"


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crawl_run_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("crawl_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # SEO fields
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    h1: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    headings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # h2, h3 lists
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Technical
    is_indexable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=True)
    has_structured_data: Mapped[bool] = mapped_column(Boolean, default=False)
    structured_data: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    open_graph: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    twitter_card: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Performance (when available)
    lcp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cls: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    page_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Content analysis
    is_thin_content: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_keyword: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Raw signals for agents
    signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    depth: Mapped[int] = mapped_column(Integer, default=0)
    is_orphan: Mapped[bool] = mapped_column(Boolean, default=False)

    crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    website = relationship("Website", back_populates="pages")
    crawl_run = relationship("CrawlRun", back_populates="pages")

    def __repr__(self) -> str:
        return f"<Page {self.url}>"
