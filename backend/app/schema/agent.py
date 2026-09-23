"""Schema / structured data generation agent – never misleading."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


class SchemaAgent:
    """Recommend accurate JSON-LD based on page signals."""

    def recommend_for_page(self, page: dict[str, Any], site_url: str, site_name: str | None = None) -> list[dict[str, Any]]:
        url = page.get("url") or site_url
        title = page.get("title") or ""
        description = page.get("meta_description") or ""
        h1 = page.get("h1") or title
        existing = page.get("structured_data") or []
        existing_types = set()
        for block in existing:
            if isinstance(block, dict):
                t = block.get("@type")
                if isinstance(t, list):
                    existing_types.update(t)
                elif t:
                    existing_types.add(t)
            elif isinstance(block, list):
                for b in block:
                    if isinstance(b, dict) and b.get("@type"):
                        existing_types.add(b["@type"])

        recommendations = []
        domain = urlparse(site_url).hostname or ""
        org_name = site_name or domain

        # WebSite + SearchAction only on homepage
        path = urlparse(url).path or "/"
        is_home = path in ("", "/")

        if is_home and "WebSite" not in existing_types:
            recommendations.append({
                "type": "WebSite",
                "reason": "Homepage should declare WebSite schema for sitelinks search box eligibility.",
                "json_ld": {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": org_name,
                    "url": site_url.rstrip("/") + "/",
                },
            })

        if is_home and "Organization" not in existing_types:
            recommendations.append({
                "type": "Organization",
                "reason": "Organization schema helps establish entity identity.",
                "json_ld": {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": org_name,
                    "url": site_url.rstrip("/") + "/",
                },
            })

        # WebPage for content pages
        if "WebPage" not in existing_types and not is_home:
            recommendations.append({
                "type": "WebPage",
                "reason": "WebPage schema clarifies the page entity.",
                "json_ld": {
                    "@context": "https://schema.org",
                    "@type": "WebPage",
                    "name": title or h1,
                    "description": description or None,
                    "url": url,
                    "isPartOf": {"@type": "WebSite", "url": site_url.rstrip("/") + "/"},
                },
            })

        # Detect tool/calculator pages
        tool_signals = any(
            x in (url + " " + title + " " + h1).lower()
            for x in ("calculator", "converter", "generator", "tool", "checker", "counter")
        )
        if tool_signals and "SoftwareApplication" not in existing_types and "WebApplication" not in existing_types:
            recommendations.append({
                "type": "SoftwareApplication",
                "reason": "Utility/tool pages benefit from SoftwareApplication schema.",
                "json_ld": {
                    "@context": "https://schema.org",
                    "@type": "SoftwareApplication",
                    "name": h1 or title,
                    "operatingSystem": "Web",
                    "applicationCategory": "UtilitiesApplication",
                    "offers": {
                        "@type": "Offer",
                        "price": "0",
                        "priceCurrency": "USD",
                    },
                    "url": url,
                },
            })

        # FAQ if page has question-like headings
        headings = page.get("headings") or {}
        h2s = headings.get("h2") or []
        h3s = headings.get("h3") or []
        qa_heads = [h for h in (h2s + h3s) if "?" in h or h.lower().startswith(("how ", "what ", "why ", "when ", "where ", "can "))]
        if len(qa_heads) >= 2 and "FAQPage" not in existing_types:
            entities = []
            for q in qa_heads[:8]:
                entities.append({
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"See the section '{q}' on this page for details.",
                    },
                })
            recommendations.append({
                "type": "FAQPage",
                "reason": "Question-style headings detected – FAQPage can enable FAQ rich results.",
                "json_ld": {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": entities,
                },
                "note": "Replace placeholder answers with real content before publishing.",
            })

        # BreadcrumbList for deep pages
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) >= 1 and "BreadcrumbList" not in existing_types:
            items = [{
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": site_url.rstrip("/") + "/",
            }]
            acc = site_url.rstrip("/")
            for i, part in enumerate(parts, start=2):
                acc = acc + "/" + part
                items.append({
                    "@type": "ListItem",
                    "position": i,
                    "name": part.replace("-", " ").replace("_", " ").title(),
                    "item": acc,
                })
            recommendations.append({
                "type": "BreadcrumbList",
                "reason": "Breadcrumbs improve navigation understanding in search.",
                "json_ld": {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": items,
                },
            })

        return recommendations

    def analyze_site(self, pages: list[dict[str, Any]], site_url: str, site_name: str | None = None) -> list[dict[str, Any]]:
        out = []
        for p in pages:
            if (p.get("status_code") or 0) != 200:
                continue
            recs = self.recommend_for_page(p, site_url, site_name)
            for r in recs:
                out.append({**r, "page_url": p.get("url")})
        return out
