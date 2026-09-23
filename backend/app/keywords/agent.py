"""Keyword research agent – extracts primary/secondary/long-tail keywords per page."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse


STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "must", "shall", "can", "need", "dare", "ought", "used", "this", "that", "these",
    "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "its", "our", "their", "what", "which", "who",
    "whom", "whose", "where", "when", "why", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "also", "now", "here",
    "there", "then", "once", "if", "as", "into", "over", "after", "before", "between",
    "under", "again", "further", "above", "below", "up", "down", "out", "off",
    "about", "against", "during", "without", "within", "along", "across", "behind",
    "beyond", "plus", "except", "page", "home", "click", "read", "learn", "get",
    "use", "using", "used", "new", "best", "free", "online", "www", "http", "https",
    "com", "net", "org", "html", "php", "asp",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{1,}", (text or "").lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def detect_intent(keyword: str, title: str = "", url: str = "") -> str:
    kw = (keyword + " " + title + " " + url).lower()
    if any(x in kw for x in ("buy", "price", "pricing", "order", "shop", "cart", "deal", "discount", "subscribe")):
        return "transactional"
    if any(x in kw for x in ("best", "vs", "versus", "compare", "review", "top", "alternative")):
        return "commercial"
    if any(x in kw for x in ("login", "sign in", "dashboard", "account", "my ")):
        return "navigational"
    return "informational"


def path_keywords(url: str) -> list[str]:
    path = urlparse(url).path or ""
    parts = [p for p in path.strip("/").split("/") if p and p not in ("index", "page", "en", "blog")]
    cleaned = []
    for p in parts:
        p = re.sub(r"[-_]+", " ", p)
        p = re.sub(r"\.(html|php|aspx?)$", "", p, flags=re.I)
        if len(p) > 2:
            cleaned.append(p.lower())
    return cleaned


class KeywordAgent:
    """Generate keyword strategy for each crawled page without external APIs."""

    def analyze_page(self, page: dict[str, Any]) -> list[dict[str, Any]]:
        url = page.get("url") or ""
        title = page.get("title") or ""
        h1 = page.get("h1") or ""
        meta = page.get("meta_description") or ""
        headings = page.get("headings") or {}
        h2s = headings.get("h2") or []
        h3s = headings.get("h3") or []

        # Corpus for frequency
        corpus_parts = [title, h1, meta] + h2s[:8] + h3s[:8] + path_keywords(url)
        corpus = " ".join(str(x) for x in corpus_parts if x)
        tokens = tokenize(corpus)

        unigrams = Counter(tokens)
        bigrams = Counter(ngrams(tokens, 2))
        trigrams = Counter(ngrams(tokens, 3))

        # Primary: prefer path segment or H1/title phrase
        primary = None
        path_kws = path_keywords(url)
        if path_kws:
            primary = path_kws[-1]  # deepest path segment often is the topic
        if not primary and h1:
            primary = " ".join(tokenize(h1)[:4]) or h1[:60]
        if not primary and title:
            primary = " ".join(tokenize(title)[:4]) or title[:60]
        if not primary and unigrams:
            primary = unigrams.most_common(1)[0][0]
        if not primary:
            primary = "page content"

        primary = primary.strip()[:80]

        results: list[dict[str, Any]] = []
        results.append({
            "keyword": primary,
            "type": "primary",
            "search_intent": detect_intent(primary, title, url),
            "recommended_title": self._title(primary, title),
            "recommended_h1": self._h1(primary, h1),
            "recommended_meta": self._meta(primary, meta, title),
        })

        # Secondary from bigrams / strong unigrams
        secondary_candidates = [p for p, _ in bigrams.most_common(8)]
        secondary_candidates += [w for w, _ in unigrams.most_common(10) if w not in primary]
        seen = {primary.lower()}
        for cand in secondary_candidates:
            if cand.lower() in seen or len(cand) < 3:
                continue
            seen.add(cand.lower())
            results.append({
                "keyword": cand[:80],
                "type": "secondary",
                "search_intent": detect_intent(cand, title, url),
                "recommended_title": None,
                "recommended_h1": None,
                "recommended_meta": None,
            })
            if len([r for r in results if r["type"] == "secondary"]) >= 5:
                break

        # Long-tail from trigrams
        for cand, _ in trigrams.most_common(6):
            if cand.lower() in seen:
                continue
            seen.add(cand.lower())
            results.append({
                "keyword": cand[:100],
                "type": "long_tail",
                "search_intent": detect_intent(cand, title, url),
                "recommended_title": None,
                "recommended_h1": None,
                "recommended_meta": None,
            })
            if len([r for r in results if r["type"] == "long_tail"]) >= 4:
                break

        return results

    def analyze_site(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return flat list of keyword records with page url attached."""
        out = []
        for p in pages:
            if (p.get("status_code") or 0) != 200:
                continue
            for kw in self.analyze_page(p):
                out.append({**kw, "page_url": p.get("url")})
        return out

    def _title(self, primary: str, current: str) -> str:
        base = primary.title() if primary.islower() else primary
        if current and primary.lower() in current.lower():
            # keep current if already good length
            if 30 <= len(current) <= 65:
                return current
        return f"{base} – Free Online Tool" if "calculator" in primary.lower() or "tool" in primary.lower() else f"{base} | Guide & Tips"

    def _h1(self, primary: str, current: str) -> str:
        if current and len(current) > 5:
            return current
        return primary.title() if primary.islower() else primary

    def _meta(self, primary: str, current: str, title: str) -> str:
        if current and 70 <= len(current) <= 165:
            return current
        topic = primary if primary else title
        return (
            f"Use our free {topic} to get instant, accurate results. "
            f"Simple, fast, and mobile-friendly. No signup required."
        )[:160]
