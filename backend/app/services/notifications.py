"""Notification stubs – email/webhook hooks for crawl complete and score drops."""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("seo.notifications")


async def notify_crawl_complete(
    email: Optional[str],
    website_url: str,
    score: Optional[float],
    crawl_status: str,
) -> dict[str, Any]:
    """
    Production: plug SMTP / Resend / SES here.
    Never claim ranking improvements in message body.
    """
    subject = f"[SEO Autopilot] Crawl {crawl_status}: {website_url}"
    body = (
        f"Crawl finished with status={crawl_status}.\n"
        f"Website: {website_url}\n"
        f"SEO score: {score if score is not None else 'n/a'}/100\n\n"
        "Recommended optimizations and estimated impact only. Rankings are never guaranteed.\n"
    )
    if not email:
        logger.info("notify_crawl_complete skipped (no email): %s", subject)
        return {"sent": False, "reason": "no_email"}
    logger.info("notify_crawl_complete to=%s subject=%s", email, subject)
    # Stub – log only
    return {"sent": False, "reason": "email_provider_not_configured", "preview": {"subject": subject, "body": body}}


async def notify_score_drop(
    email: Optional[str],
    website_url: str,
    old_score: float,
    new_score: float,
    threshold: int,
) -> dict[str, Any]:
    drop = old_score - new_score
    if drop < threshold:
        return {"sent": False, "reason": "below_threshold"}
    subject = f"[SEO Autopilot] Score drop on {website_url}"
    body = (
        f"Score changed from {old_score} to {new_score} (drop {drop:.0f}).\n"
        "Review recommendations in the dashboard.\n"
        "Potential SEO improvement only — rankings are never guaranteed.\n"
    )
    logger.info("notify_score_drop to=%s drop=%.1f", email, drop)
    return {"sent": False, "reason": "email_provider_not_configured", "preview": {"subject": subject, "body": body}}
