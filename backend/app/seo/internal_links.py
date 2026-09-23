"""Internal linking graph agent."""
from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlparse


class InternalLinkAgent:
    def build_graph(self, pages: list[dict[str, Any]]) -> dict[str, Any]:
        nodes = []
        edges = []
        inbound: dict[str, int] = defaultdict(int)
        outbound: dict[str, int] = defaultdict(int)
        url_set = set()

        for p in pages:
            if (p.get("status_code") or 0) != 200:
                continue
            url = p.get("url")
            if not url:
                continue
            url_set.add(url)
            for link in p.get("internal_links") or []:
                t = link.get("url")
                if t:
                    outbound[url] += 1
                    inbound[t] += 1
                    edges.append({
                        "from": url,
                        "to": t,
                        "anchor": (link.get("text") or "")[:80],
                    })

        orphans = []
        weak = []
        important = []

        for p in pages:
            if (p.get("status_code") or 0) != 200:
                continue
            url = p.get("url")
            if not url:
                continue
            in_c = inbound.get(url, 0)
            out_c = outbound.get(url, 0)
            path = urlparse(url).path or "/"
            is_home = path in ("", "/")
            node = {
                "url": url,
                "title": p.get("title"),
                "inbound": in_c,
                "outbound": out_c,
                "word_count": p.get("word_count") or 0,
            }
            nodes.append(node)
            if not is_home and in_c == 0:
                orphans.append(url)
            elif in_c <= 1 and not is_home:
                weak.append(url)
            if in_c >= 3 or is_home or (p.get("word_count") or 0) > 400:
                important.append(url)

        opportunities = []
        for orphan in orphans[:20]:
            # link from important hubs
            for hub in important[:5]:
                if hub != orphan:
                    opportunities.append({
                        "type": "orphan_rescue",
                        "source": hub,
                        "target": orphan,
                        "why": "Orphan page has no inbound internal links.",
                        "suggested_anchor": self._anchor_from_url(orphan),
                    })
                    break

        for weak_url in weak[:15]:
            for hub in important[:3]:
                if hub != weak_url:
                    opportunities.append({
                        "type": "strengthen_weak",
                        "source": hub,
                        "target": weak_url,
                        "why": "Page has very few inbound links.",
                        "suggested_anchor": self._anchor_from_url(weak_url),
                    })
                    break

        return {
            "nodes": nodes,
            "edges_count": len(edges),
            "orphans": orphans,
            "weak_pages": weak,
            "important_pages": important[:15],
            "opportunities": opportunities[:40],
        }

    def _anchor_from_url(self, url: str) -> str:
        path = urlparse(url).path or "/"
        part = path.strip("/").split("/")[-1] if path.strip("/") else "home"
        return part.replace("-", " ").replace("_", " ").title() or "Learn more"
