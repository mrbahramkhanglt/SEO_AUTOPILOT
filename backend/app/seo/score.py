"""SEO score calculator (0-100)."""
from __future__ import annotations

from typing import Any


def compute_seo_score(crawl_result: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    pages = crawl_result.get("pages") or []
    total = max(len(pages), 1)

    def ratio_ok(predicate) -> float:
        if not pages:
            return 0.5
        ok = sum(1 for p in pages if predicate(p))
        return ok / total

    # Category scores (0-100)
    technical = 100
    if not crawl_result.get("robots_txt"):
        technical -= 10
    if not crawl_result.get("sitemap_urls"):
        technical -= 15
    non_200 = sum(1 for p in pages if (p.get("status_code") or 0) != 200)
    technical -= min(30, non_200 * 5)
    technical = max(0, technical)

    on_page = int(
        100
        * (
            0.35 * ratio_ok(lambda p: bool((p.get("title") or "").strip()))
            + 0.25 * ratio_ok(lambda p: bool((p.get("meta_description") or "").strip()))
            + 0.25 * ratio_ok(lambda p: bool(p.get("h1")))
            + 0.15 * ratio_ok(lambda p: (p.get("images_missing_alt") or 0) == 0)
        )
    )

    content = int(100 * ratio_ok(lambda p: not p.get("is_thin_content") and (p.get("word_count") or 0) >= 150))

    performance = 70  # placeholder until CWV collected
    indexability = int(100 * ratio_ok(lambda p: p.get("is_indexable", True)))
    structured_data = int(100 * ratio_ok(lambda p: p.get("has_structured_data")))
    internal_linking = int(
        100 * ratio_ok(lambda p: len(p.get("internal_links") or []) >= 2)
    )
    mobile = 75  # placeholder
    accessibility = int(
        100 * ratio_ok(lambda p: (p.get("images_missing_alt") or 0) == 0)
    )
    authority = 50  # needs external data

    # Penalty from critical/high issues
    critical = sum(1 for i in issues if i.get("severity") == "critical")
    high = sum(1 for i in issues if i.get("severity") == "high")
    penalty = min(25, critical * 8 + high * 3)

    overall = int(
        (
            technical * 0.18
            + on_page * 0.20
            + content * 0.15
            + performance * 0.10
            + indexability * 0.12
            + structured_data * 0.08
            + internal_linking * 0.07
            + mobile * 0.05
            + accessibility * 0.03
            + authority * 0.02
        )
        - penalty
    )
    overall = max(0, min(100, overall))

    return {
        "overall": overall,
        "technical": max(0, min(100, technical)),
        "on_page": max(0, min(100, on_page)),
        "content": max(0, min(100, content)),
        "performance": performance,
        "indexability": max(0, min(100, indexability)),
        "structured_data": max(0, min(100, structured_data)),
        "internal_linking": max(0, min(100, internal_linking)),
        "mobile": mobile,
        "accessibility": max(0, min(100, accessibility)),
        "authority": authority,
        "details": {
            "pages_analyzed": len(pages),
            "critical_issues": critical,
            "high_issues": high,
            "penalty_applied": penalty,
        },
    }
