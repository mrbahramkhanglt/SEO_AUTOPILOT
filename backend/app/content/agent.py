"""Content analysis & opportunity agent – no spam, intent-aligned."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


class ContentAgent:
    def analyze_site(self, pages: list[dict[str, Any]], keywords: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        opportunities: list[dict[str, Any]] = []
        tool_pages = []
        thin_pages = []
        no_faq = []

        for p in pages:
            if (p.get("status_code") or 0) != 200:
                continue
            url = p.get("url") or ""
            title = (p.get("title") or "").lower()
            h1 = (p.get("h1") or "").lower()
            wc = p.get("word_count") or 0
            path = urlparse(url).path or "/"

            is_tool = any(x in (url + title + h1) for x in ("calculator", "converter", "generator", "tool", "checker"))
            if is_tool:
                tool_pages.append(p)
            if p.get("is_thin_content") or wc < 150:
                thin_pages.append(p)

            headings = p.get("headings") or {}
            h2s = headings.get("h2") or []
            if is_tool and not any("faq" in (h or "").lower() or "?" in (h or "") for h in h2s):
                no_faq.append(p)

        # Tool page content template opportunities
        for p in tool_pages[:15]:
            name = p.get("h1") or p.get("title") or urlparse(p.get("url") or "").path
            opportunities.append({
                "type": "tool_page_enhancement",
                "page_url": p.get("url"),
                "title": f"Expand content for: {name}",
                "what": "Tool page needs supporting educational content around the utility.",
                "why": "Thin tool pages rarely rank; users and search engines expect how-to, examples, and FAQ.",
                "how": (
                    "Add sections: How to use, Examples, Formula/logic (if relevant), "
                    "Limitations, FAQ (3–5 real questions), Related tools."
                ),
                "impact": "high",
                "effort": "medium",
                "content_outline": [
                    f"H1: {name}",
                    "Short intro (2–3 sentences, intent-aligned)",
                    "How to use (numbered steps)",
                    "Worked example",
                    "Formula or methodology (if applicable)",
                    "FAQ (3–5 questions)",
                    "Related tools (internal links)",
                ],
            })

        for p in thin_pages:
            if p in tool_pages:
                continue  # already covered
            opportunities.append({
                "type": "thin_content",
                "page_url": p.get("url"),
                "title": f"Thin content: {p.get('title') or p.get('url')}",
                "what": f"Page has only ~{p.get('word_count') or 0} words.",
                "why": "Thin pages struggle to rank and may dilute site quality.",
                "how": "Expand with useful, original content matching search intent — or consolidate/noindex if low-value.",
                "impact": "high",
                "effort": "hard",
            })

        # Topic cluster suggestion from primary keywords
        if keywords:
            primaries = [k for k in keywords if k.get("type") == "primary"]
            # Group by first word
            clusters: dict[str, list[str]] = {}
            for k in primaries[:40]:
                kw = k.get("keyword") or ""
                root = kw.split()[0] if kw else ""
                if root:
                    clusters.setdefault(root, []).append(kw)
            for root, members in list(clusters.items())[:5]:
                if len(members) >= 2:
                    opportunities.append({
                        "type": "topic_cluster",
                        "page_url": None,
                        "title": f"Topic cluster opportunity: {root}",
                        "what": f"Related keywords detected: {', '.join(members[:6])}",
                        "why": "Topic clusters strengthen topical authority and internal linking.",
                        "how": "Create a pillar page + supporting articles, interlink them with descriptive anchors.",
                        "impact": "medium",
                        "effort": "hard",
                        "keywords": members[:8],
                    })

        return opportunities
