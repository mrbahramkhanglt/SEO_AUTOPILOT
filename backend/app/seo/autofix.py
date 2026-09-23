"""Auto-fix engine – generates safe SEO artifacts for download or deploy."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse
from xml.sax.saxutils import escape


class AutoFixEngine:
    """
    Produces downloadable/safe fixes:
    - robots.txt
    - sitemap.xml
    - per-page metadata CSV/JSON
    - JSON-LD blocks
    Never creates spam or doorway pages.
    """

    def generate(
        self,
        website_url: str,
        pages: list[dict[str, Any]],
        schema_recs: list[dict[str, Any]] | None = None,
        keyword_recs: list[dict[str, Any]] | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        domain = domain or (urlparse(website_url).hostname or "example.com")
        base = website_url.rstrip("/")

        robots = self._robots(base)
        sitemap = self._sitemap(pages, base)
        metadata = self._metadata_fixes(pages, keyword_recs or [])
        schemas = self._schema_blocks(schema_recs or [])
        internal_links = self._internal_link_suggestions(pages)

        return {
            "robots_txt": robots,
            "sitemap_xml": sitemap,
            "metadata_fixes": metadata,
            "schema_blocks": schemas,
            "internal_link_suggestions": internal_links,
            "summary": {
                "pages_in_sitemap": len([p for p in pages if (p.get("status_code") or 0) == 200]),
                "metadata_rows": len(metadata),
                "schema_blocks": len(schemas),
                "internal_link_suggestions": len(internal_links),
            },
        }

    def _robots(self, base: str) -> str:
        return (
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            f"Sitemap: {base}/sitemap.xml\n"
        )

    def _sitemap(self, pages: list[dict[str, Any]], base: str) -> str:
        urls = []
        seen = set()
        for p in pages:
            if (p.get("status_code") or 0) != 200:
                continue
            if not p.get("is_indexable", True):
                continue
            u = p.get("canonical_url") or p.get("url")
            if not u or u in seen:
                continue
            seen.add(u)
            urls.append(u)
        if not urls:
            urls = [base + "/"]

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for u in urls[:5000]:
            lines.append("  <url>")
            lines.append(f"    <loc>{escape(u)}</loc>")
            lines.append("  </url>")
        lines.append("</urlset>")
        return "\n".join(lines) + "\n"

    def _metadata_fixes(
        self, pages: list[dict[str, Any]], keywords: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        # Map primary keyword suggestions by page URL
        by_url: dict[str, dict] = {}
        for k in keywords:
            if k.get("type") != "primary":
                continue
            url = k.get("page_url")
            if url:
                by_url[url] = k

        rows = []
        for p in pages:
            if (p.get("status_code") or 0) != 200:
                continue
            url = p.get("url") or ""
            kw = by_url.get(url) or {}
            title = p.get("title") or ""
            meta = p.get("meta_description") or ""
            h1 = p.get("h1") or ""

            rec_title = kw.get("recommended_title")
            rec_meta = kw.get("recommended_meta")
            rec_h1 = kw.get("recommended_h1")

            needs = False
            if not title or len(title) < 15 or len(title) > 70:
                needs = True
            if not meta or len(meta) < 50:
                needs = True
            if not h1:
                needs = True

            if needs or rec_title or rec_meta:
                rows.append({
                    "url": url,
                    "current_title": title,
                    "recommended_title": rec_title or title,
                    "current_meta": meta,
                    "recommended_meta": rec_meta or meta,
                    "current_h1": h1,
                    "recommended_h1": rec_h1 or h1,
                    "primary_keyword": kw.get("keyword"),
                    "search_intent": kw.get("search_intent"),
                })
        return rows

    def _schema_blocks(self, schema_recs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocks = []
        for s in schema_recs:
            ld = s.get("json_ld")
            if not ld:
                continue
            blocks.append({
                "page_url": s.get("page_url"),
                "schema_type": s.get("type"),
                "json_ld": ld,
                "script_tag": (
                    '<script type="application/ld+json">\n'
                    + json.dumps(ld, indent=2, ensure_ascii=False)
                    + "\n</script>"
                ),
                "reason": s.get("reason"),
                "note": s.get("note"),
            })
        return blocks

    def _internal_link_suggestions(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Suggest contextual links from thin/orphan-ish pages to stronger pages."""
        indexable = [p for p in pages if (p.get("status_code") or 0) == 200]
        if len(indexable) < 2:
            return []

        # Score pages by content richness
        ranked = sorted(
            indexable,
            key=lambda p: (p.get("word_count") or 0) + len(p.get("internal_links") or []) * 5,
            reverse=True,
        )
        hubs = ranked[:5]
        suggestions = []

        for p in indexable:
            links = p.get("internal_links") or []
            link_urls = {l.get("url") for l in links}
            if len(links) >= 5:
                continue
            targets = []
            for hub in hubs:
                hu = hub.get("url")
                if hu and hu != p.get("url") and hu not in link_urls:
                    anchor = hub.get("h1") or hub.get("title") or "Related page"
                    targets.append({
                        "target_url": hu,
                        "suggested_anchor": (anchor or "")[:60],
                    })
                if len(targets) >= 3:
                    break
            if targets:
                suggestions.append({
                    "source_url": p.get("url"),
                    "current_internal_links": len(links),
                    "add_links": targets,
                    "why": "Increase internal links to important pages for better crawl paths and relevance.",
                })
        return suggestions[:40]
