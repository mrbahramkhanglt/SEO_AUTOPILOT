"""Master Orchestrator Agent – high-level control surface for the SEO pipeline."""
from __future__ import annotations

from typing import Any

from app.services.orchestrator import run_full_pipeline


class MasterOrchestratorAgent:
    """
    Controls workflow, assigns tasks, tracks state, retries failures, validates outputs.
    Never blindly applies unsafe changes – auto-fix is limited to safe artifact generation
    unless integrations + approval settings allow more.
    """

    SAFE_AUTO = {
        "metadata", "alt_text", "schema_fixes", "sitemap", "robots", "internal_links_suggestions",
    }
    REQUIRES_APPROVAL = {
        "url_changes", "delete_pages", "major_content_rewrite", "redirects", "navigation", "production_config",
    }

    def classify_change(self, change_type: str) -> str:
        if change_type in self.SAFE_AUTO:
            return "auto_approve"
        if change_type in self.REQUIRES_APPROVAL:
            return "require_approval"
        return "require_approval"

    async def run(self, db, website_id: str, crawl_run_id: str) -> None:
        await run_full_pipeline(db, website_id, crawl_run_id)

    def validate_output(self, payload: dict[str, Any]) -> list[str]:
        errors = []
        if "overall" in payload and not (0 <= int(payload["overall"]) <= 100):
            errors.append("score out of range")
        return errors
