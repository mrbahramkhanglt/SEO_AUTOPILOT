"""Applied SEO changes with audit trail."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from app.database.types import JSONType as JSONB, UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Change(Base):
    __tablename__ = "changes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    website_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True
    )

    change_type: Mapped[str] = mapped_column(String(100), nullable=False)  # metadata, schema, sitemap, content, ...
    description: Mapped[str] = mapped_column(Text, nullable=False)

    before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="proposed"
    )  # proposed, approved, applied, verified, rolled_back, failed
    applied_via: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # github, wordpress, download, ...

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    website = relationship("Website", back_populates="changes")
