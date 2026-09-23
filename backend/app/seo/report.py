"""Professional SEO report generator."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ReportGenerator:
    def generate(
        self,
        website: dict[str, Any],
        score: dict[str, Any] | None,
        issues: list[dict[str, Any]],
        keywords: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
        crawl: dict[str, Any] | None = None,
        autofix_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        critical = [i for i in issues if i.get("severity") == "critical"]
        high = [i for i in issues if i.get("severity") == "high"]
        medium = [i for i in issues if i.get("severity") == "medium"]
        low = [i for i in issues if i.get("severity") == "low"]

        primaries = [k for k in keywords if k.get("type") == "primary"][:20]
        top_recs = sorted(recommendations, key=lambda r: -float(r.get("priority") or 0))[:15]

        overall = (score or {}).get("overall")
        summary_lines = []
        if overall is not None:
            summary_lines.append(
                f"Overall SEO score is {overall}/100 for {website.get('domain') or website.get('url')}."
            )
        summary_lines.append(
            f"Found {len(critical)} critical, {len(high)} high, {len(medium)} medium, and {len(low)} low issues."
        )
        if crawl:
            summary_lines.append(
                f"Crawled {crawl.get('pages_crawled') or 0} pages "
                f"(discovered {crawl.get('pages_discovered') or 0})."
            )
        summary_lines.append(
            "Recommendations focus on potential SEO improvement — rankings are never guaranteed."
        )

        return {
            "title": f"SEO Audit Report – {website.get('domain') or website.get('url')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "website": {
                "url": website.get("url"),
                "domain": website.get("domain"),
                "name": website.get("name"),
                "has_sitemap": website.get("has_sitemap"),
                "has_robots": website.get("has_robots"),
                "technology_stack": website.get("technology_stack"),
            },
            "executive_summary": " ".join(summary_lines),
            "seo_score": score,
            "critical_issues": critical,
            "high_issues": high,
            "medium_issues": medium,
            "low_issues": low,
            "keyword_opportunities": primaries,
            "top_recommendations": top_recs,
            "autofix_summary": autofix_summary,
            "next_steps": [
                "Review and apply auto-applicable metadata and schema fixes.",
                "Expand thin tool pages with how-to, examples, and FAQ content.",
                "Submit updated sitemap in Google Search Console after deploy.",
                "Re-crawl after changes to verify before/after impact.",
                "Monitor rankings and CTR — treat all gains as potential improvements only.",
            ],
            "disclaimer": (
                "This report provides recommended optimizations and estimated impact only. "
                "SEO Autopilot AI never claims that rankings will increase or that any page will rank #1."
            ),
        }
