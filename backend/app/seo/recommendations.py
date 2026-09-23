"""AI Recommendation agent – prioritizes fixes with WHAT/WHY/HOW/IMPACT."""
from __future__ import annotations

from typing import Any


class RecommendationAgent:
    def build(
        self,
        issues: list[dict[str, Any]],
        schema_recs: list[dict[str, Any]] | None = None,
        content_opps: list[dict[str, Any]] | None = None,
        keyword_recs: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []

        for iss in issues:
            auto = iss.get("code") in {
                "MISSING_META_DESCRIPTION",
                "MISSING_TITLE",
                "MISSING_H1",
                "MISSING_IMAGE_ALT",
                "MISSING_CANONICAL",
                "MISSING_ROBOTS",
                "MISSING_SITEMAP",
                "MISSING_SCHEMA",
                "MISSING_OPEN_GRAPH",
            }
            recs.append({
                "category": iss.get("category") or "technical",
                "title": iss.get("title") or iss.get("code"),
                "what": iss.get("description") or iss.get("title"),
                "why": iss.get("why_it_matters") or "",
                "how": iss.get("recommended_fix") or "",
                "impact": iss.get("expected_impact") or "medium",
                "effort": iss.get("effort") or "medium",
                "priority": float(iss.get("priority_score") or 50),
                "auto_applicable": auto,
                "requires_approval": not auto,
                "suggested_change": {
                    "issue_code": iss.get("code"),
                    "data": iss.get("data"),
                },
                "source": "issue",
            })

        for s in schema_recs or []:
            recs.append({
                "category": "structured_data",
                "title": f"Add {s.get('type')} schema",
                "what": f"Recommend adding {s.get('type')} JSON-LD on {s.get('page_url')}",
                "why": s.get("reason") or "Structured data enables richer search appearance.",
                "how": "Add the provided JSON-LD in a <script type=\"application/ld+json\"> block.",
                "impact": "medium",
                "effort": "easy",
                "priority": 55.0,
                "auto_applicable": True,
                "requires_approval": False,
                "suggested_change": {
                    "schema_type": s.get("type"),
                    "json_ld": s.get("json_ld"),
                    "page_url": s.get("page_url"),
                    "note": s.get("note"),
                },
                "source": "schema",
            })

        for c in content_opps or []:
            impact = c.get("impact") or "medium"
            priority = {"high": 70, "medium": 50, "low": 30}.get(impact, 50)
            recs.append({
                "category": "content",
                "title": c.get("title") or "Content opportunity",
                "what": c.get("what") or "",
                "why": c.get("why") or "",
                "how": c.get("how") or "",
                "impact": impact,
                "effort": c.get("effort") or "medium",
                "priority": float(priority),
                "auto_applicable": False,
                "requires_approval": True,
                "suggested_change": {
                    "type": c.get("type"),
                    "page_url": c.get("page_url"),
                    "content_outline": c.get("content_outline"),
                    "keywords": c.get("keywords"),
                },
                "source": "content",
            })

        # Keyword title/meta suggestions for primary keywords
        for k in keyword_recs or []:
            if k.get("type") != "primary":
                continue
            if k.get("recommended_title") or k.get("recommended_meta"):
                recs.append({
                    "category": "on_page",
                    "title": f"Optimize metadata for “{k.get('keyword')}”",
                    "what": f"Primary keyword identified: {k.get('keyword')} ({k.get('search_intent')} intent)",
                    "why": "Aligned title/H1/meta improve relevance and CTR potential.",
                    "how": "Apply recommended title, H1 and meta description where they improve on current values.",
                    "impact": "medium",
                    "effort": "easy",
                    "priority": 60.0,
                    "auto_applicable": True,
                    "requires_approval": False,
                    "suggested_change": {
                        "keyword": k.get("keyword"),
                        "page_url": k.get("page_url"),
                        "recommended_title": k.get("recommended_title"),
                        "recommended_h1": k.get("recommended_h1"),
                        "recommended_meta": k.get("recommended_meta"),
                        "search_intent": k.get("search_intent"),
                    },
                    "source": "keyword",
                })

        recs.sort(key=lambda r: -r["priority"])
        return recs
