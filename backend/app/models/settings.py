"""Organization and system settings (admin-configurable)."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.database.types import UUIDType as UUID, JSONType as JSONB


class SystemSetting(Base):
    """Global platform settings – superuser / admin only."""
    __tablename__ = "system_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OrganizationSettings(Base):
    """Per-organization admin configuration."""
    __tablename__ = "organization_settings"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_org_settings"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Crawl defaults
    default_max_pages: Mapped[int] = mapped_column(Integer, default=50)
    default_max_depth: Mapped[int] = mapped_column(Integer, default=4)
    default_crawl_delay: Mapped[float] = mapped_column(Float, default=0.3)

    # AI
    ai_provider: Mapped[str] = mapped_column(String(50), default="rules")  # rules | openai | anthropic | gemini
    ai_api_key_set: Mapped[bool] = mapped_column(Boolean, default=False)  # never store raw key in plain responses
    # Encrypted/stored key lives in secrets JSON – not returned by API
    secrets: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Integrations toggles
    github_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    netlify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    vercel_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    gsc_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ga4_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    wordpress_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Safety
    auto_optimize_default: Mapped[bool] = mapped_column(Boolean, default=False)
    require_approval_default: Mapped[bool] = mapped_column(Boolean, default=True)
    max_websites_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Branding
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    report_footer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notification
    alert_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    notify_on_crawl_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_score_drop: Mapped[bool] = mapped_column(Boolean, default=True)
    score_drop_threshold: Mapped[int] = mapped_column(Integer, default=5)

    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
