"""Technical SEO analysis agent."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


class TechnicalSEOAgent:
    """Analyzes technical SEO signals from crawl results."""

    def analyze(self, crawl_result: dict[str, Any], website_url: str) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        pages = crawl_result.get("pages") or []
        domain = crawl_result.get("domain") or urlparse(website_url).hostname or ""

        # Site-level
        if not website_url.startswith("https://"):
            issues.append(self._issue(
                "technical", "NO_HTTPS", "critical",
                "Website is not served over HTTPS",
                "HTTP sites are flagged as not secure and lose ranking signals.",
                "Enable HTTPS and redirect all HTTP traffic to HTTPS.",
                "high", "medium",
            ))

        if not crawl_result.get("robots_txt"):
            issues.append(self._issue(
                "technical", "MISSING_ROBOTS", "medium",
                "robots.txt not found",
                "Search engines look for robots.txt to understand crawl rules.",
                "Add a robots.txt at the site root with sensible Allow/Disallow rules and a Sitemap directive.",
                "medium", "easy",
            ))

        if not crawl_result.get("sitemap_urls"):
            issues.append(self._issue(
                "technical", "MISSING_SITEMAP", "high",
                "XML sitemap not found",
                "Sitemaps help search engines discover all important pages.",
                "Generate and submit an XML sitemap; reference it in robots.txt.",
                "high", "easy",
            ))

        # Page-level aggregation
        missing_title = 0
        missing_meta = 0
        missing_h1 = 0
        multi_h1 = 0
        no_canonical = 0
        thin = 0
        missing_alt_pages = 0
        non_200 = 0
        no_schema = 0
        no_og = 0

        titles_seen: dict[str, int] = {}
        for p in pages:
            if p.get("error") or not p.get("status_code"):
                non_200 += 1
                continue
            sc = p.get("status_code") or 0
            if sc != 200:
                non_200 += 1

            title = (p.get("title") or "").strip()
            if not title:
                missing_title += 1
            else:
                titles_seen[title] = titles_seen.get(title, 0) + 1

            if not (p.get("meta_description") or "").strip():
                missing_meta += 1

            h1s = (p.get("headings") or {}).get("h1") or []
            if not h1s:
                missing_h1 += 1
            elif len(h1s) > 1:
                multi_h1 += 1

            if not p.get("canonical_url"):
                no_canonical += 1

            if p.get("is_thin_content"):
                thin += 1

            if (p.get("images_missing_alt") or 0) > 0:
                missing_alt_pages += 1

            if not p.get("has_structured_data"):
                no_schema += 1

            if not p.get("open_graph"):
                no_og += 1

        total = max(len(pages), 1)

        if missing_title:
            issues.append(self._issue(
                "on_page", "MISSING_TITLE", "critical" if missing_title / total > 0.3 else "high",
                f"{missing_title} page(s) missing <title>",
                "Titles are a primary ranking and CTR signal in search results.",
                "Write unique, descriptive titles (50–60 characters) including the primary keyword.",
                "high", "easy",
                data={"count": missing_title},
            ))

        dup_titles = {t: c for t, c in titles_seen.items() if c > 1}
        if dup_titles:
            issues.append(self._issue(
                "on_page", "DUPLICATE_TITLES", "high",
                f"{len(dup_titles)} duplicate title(s) found",
                "Duplicate titles confuse search engines and dilute relevance.",
                "Make every page title unique and intent-aligned.",
                "high", "medium",
                data={"duplicates": list(dup_titles.keys())[:10]},
            ))

        if missing_meta:
            issues.append(self._issue(
                "on_page", "MISSING_META_DESCRIPTION", "high",
                f"{missing_meta} page(s) missing meta description",
                "Search engines may generate their own snippets; unique descriptions improve CTR.",
                "Write unique meta descriptions (140–160 chars) that match search intent.",
                "medium", "easy",
                data={"count": missing_meta},
            ))

        if missing_h1:
            issues.append(self._issue(
                "on_page", "MISSING_H1", "high",
                f"{missing_h1} page(s) missing H1",
                "H1 clarifies the main topic of the page for users and crawlers.",
                "Add a single clear H1 that includes the primary keyword naturally.",
                "high", "easy",
                data={"count": missing_h1},
            ))

        if multi_h1:
            issues.append(self._issue(
                "on_page", "MULTIPLE_H1", "medium",
                f"{multi_h1} page(s) have multiple H1 tags",
                "Multiple H1s can dilute topical focus.",
                "Use exactly one H1 per page; demote others to H2/H3.",
                "medium", "easy",
                data={"count": multi_h1},
            ))

        if no_canonical:
            issues.append(self._issue(
                "technical", "MISSING_CANONICAL", "medium",
                f"{no_canonical} page(s) without canonical tag",
                "Canonical tags prevent duplicate-content issues.",
                "Add a self-referencing rel=canonical on every indexable page.",
                "medium", "easy",
                data={"count": no_canonical},
            ))

        if thin:
            issues.append(self._issue(
                "content", "THIN_CONTENT", "high",
                f"{thin} page(s) with thin content (<150 words)",
                "Thin pages rarely rank and can hurt site quality signals.",
                "Expand useful content aligned to search intent, or consolidate/noindex low-value pages.",
                "high", "hard",
                data={"count": thin},
            ))

        if missing_alt_pages:
            issues.append(self._issue(
                "on_page", "MISSING_IMAGE_ALT", "medium",
                f"{missing_alt_pages} page(s) have images without ALT text",
                "ALT text improves accessibility and image search visibility.",
                "Add descriptive ALT attributes to meaningful images.",
                "medium", "easy",
                data={"count": missing_alt_pages},
            ))

        if non_200:
            issues.append(self._issue(
                "technical", "NON_200_STATUS", "high",
                f"{non_200} page(s) returned non-200 or failed",
                "Broken pages waste crawl budget and hurt UX.",
                "Fix 4xx/5xx errors or implement proper redirects.",
                "high", "medium",
                data={"count": non_200},
            ))

        if no_schema and pages:
            issues.append(self._issue(
                "structured_data", "MISSING_SCHEMA", "medium",
                f"{no_schema} page(s) without structured data",
                "Structured data enables rich results and clearer entity understanding.",
                "Add appropriate JSON-LD (WebPage, Article, FAQ, Product, Organization, etc.).",
                "medium", "medium",
                data={"count": no_schema},
            ))

        if no_og and pages:
            issues.append(self._issue(
                "on_page", "MISSING_OPEN_GRAPH", "low",
                f"{no_og} page(s) missing Open Graph tags",
                "OG tags control how links appear when shared on social platforms.",
                "Add og:title, og:description, og:image, og:url on key pages.",
                "low", "easy",
                data={"count": no_og},
            ))

        return issues

    def _issue(
        self,
        category: str,
        code: str,
        severity: str,
        title: str,
        why: str,
        fix: str,
        impact: str,
        effort: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        priority_map = {"critical": 100, "high": 75, "medium": 50, "low": 25}
        effort_map = {"easy": 1.2, "medium": 1.0, "hard": 0.7}
        base = priority_map.get(severity, 40)
        priority = base * effort_map.get(effort, 1.0)
        return {
            "category": category,
            "code": code,
            "severity": severity,
            "title": title,
            "description": title,
            "why_it_matters": why,
            "recommended_fix": fix,
            "expected_impact": impact,
            "effort": effort,
            "priority_score": priority,
            "data": data or {},
        }
