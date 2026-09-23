"""Third-party integrations (GitHub, Netlify, Vercel, GSC, GA4, WordPress)."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from app.database.types import JSONType as JSONB, UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    website_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("websites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # github, netlify, vercel, gsc, ga4, wordpress
    status: Mapped[str] = mapped_column(String(50), default="disconnected")  # connected, disconnected, error, expired

    # Encrypted credentials stored as JSON (tokens encrypted at rest in production)
    credentials: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # repo id, site id, etc.
    external_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    website = relationship("Website", back_populates="integrations")
