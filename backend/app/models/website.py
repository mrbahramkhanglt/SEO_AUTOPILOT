"""Website model – core entity the user onboards with a URL."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from app.database.types import JSONType as JSONB, UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Core
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Discovery
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technology_stack: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    has_sitemap: Mapped[bool] = mapped_column(Boolean, default=False)
    has_robots: Mapped[bool] = mapped_column(Boolean, default=False)
    sitemap_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    robots_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, validating, crawling, analyzing, optimizing, monitoring, error
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Settings
    max_pages: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    crawl_depth: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    auto_optimize: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    organization = relationship("Organization", back_populates="websites")
    crawl_runs = relationship("CrawlRun", back_populates="website", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="website", cascade="all, delete-orphan")
    scores = relationship("SEOScore", back_populates="website", cascade="all, delete-orphan")
    issues = relationship("SEOIssue", back_populates="website", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="website", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="website", cascade="all, delete-orphan")
    changes = relationship("Change", back_populates="website", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="website", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="website", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Website {self.domain}>"
