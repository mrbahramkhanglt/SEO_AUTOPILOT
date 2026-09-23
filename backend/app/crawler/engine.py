"""Lightweight async crawler (httpx + BeautifulSoup). Playwright optional later."""
from __future__ import annotations

import asyncio
import re
from collections import deque
from typing import Any, Optional
from urllib.parse import urljoin, urlparse, urldefrag

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.security.ssrf import SSRFError, validate_url_for_crawl

settings = get_settings()


def normalize_url(base: str, href: str) -> Optional[str]:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    try:
        full = urljoin(base, href)
        full, _ = urldefrag(full)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            return None
        # Strip trailing slash consistency except root
        path = parsed.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}{path}" + (f"?{parsed.query}" if parsed.query else "")
    except Exception:
        return None


def same_domain(url: str, root_domain: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        return host == root_domain or host.endswith("." + root_domain)
    except Exception:
        return False


class CrawlerEngine:
    def __init__(
        self,
        start_url: str,
        max_pages: int = 50,
        max_depth: int = 4,
        delay: float = 0.3,
        timeout: int = 20,
        on_progress=None,
    ):
        self.start_url = validate_url_for_crawl(start_url)
        parsed = urlparse(self.start_url)
        self.root_domain = parsed.hostname or ""
        self.base = f"{parsed.scheme}://{self.root_domain}"
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay = delay
        self.timeout = timeout
        self.on_progress = on_progress  # async callback(step, progress, message, extra)

        self.visited: set[str] = set()
        self.pages: list[dict[str, Any]] = []
        self.robots_txt: Optional[str] = None
        self.sitemap_urls: list[str] = []
        self.disallow: list[str] = []

    async def _progress(self, step: str, progress: int, message: str, **extra):
        if self.on_progress:
            await self.on_progress(step, progress, message, extra)

    async def fetch_robots(self, client: httpx.AsyncClient):
        robots_url = urljoin(self.base, "/robots.txt")
        try:
            r = await client.get(robots_url)
            if r.status_code == 200:
                self.robots_txt = r.text
                for line in r.text.splitlines():
                    low = line.lower().strip()
                    if low.startswith("disallow:"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            self.disallow.append(path)
                    if low.startswith("sitemap:"):
                        sm = line.split(":", 1)[1].strip()
                        if sm:
                            self.sitemap_urls.append(sm)
        except Exception:
            pass

    def is_allowed(self, url: str) -> bool:
        path = urlparse(url).path or "/"
        for rule in self.disallow:
            if rule == "/":
                continue  # overly broad – still allow for SEO audit
            if path.startswith(rule):
                return False
        return True

    async def fetch_sitemaps(self, client: httpx.AsyncClient):
        candidates = list(self.sitemap_urls) + [
            urljoin(self.base, p)
            for p in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml")
        ]
        seen = set()
        for sm_url in candidates:
            if sm_url in seen:
                continue
            seen.add(sm_url)
            try:
                r = await client.get(sm_url)
                if r.status_code != 200:
                    continue
                text = r.text
                if "<sitemapindex" in text:
                    # nested
                    for m in re.findall(r"<loc>\s*([^<]+)\s*</loc>", text, re.I):
                        if m not in seen:
                            self.sitemap_urls.append(m.strip())
                elif "<urlset" in text:
                    for m in re.findall(r"<loc>\s*([^<]+)\s*</loc>", text, re.I):
                        u = m.strip()
                        if same_domain(u, self.root_domain) and u not in self.visited:
                            self.sitemap_urls.append(u)
            except Exception:
                continue

    def parse_page(self, url: str, status: int, html: str, final_url: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        meta_desc = None
        md = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if md and md.get("content"):
            meta_desc = md["content"].strip()

        h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
        h3s = [h.get_text(strip=True) for h in soup.find_all("h3")]

        canonical = None
        can = soup.find("link", attrs={"rel": re.compile(r"canonical", re.I)})
        if can and can.get("href"):
            canonical = urljoin(url, can["href"])

        robots_meta = None
        rm = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if rm and rm.get("content"):
            robots_meta = rm["content"].lower()

        # Structured data
        structured = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "")
                structured.append(data)
            except Exception:
                pass

        # Open Graph
        og = {}
        for tag in soup.find_all("meta", property=re.compile(r"^og:", re.I)):
            if tag.get("property") and tag.get("content"):
                og[tag["property"]] = tag["content"]

        # Twitter
        tw = {}
        for tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
            if tag.get("name") and tag.get("content"):
                tw[tag["name"]] = tag["content"]

        # Images missing alt
        images = soup.find_all("img")
        missing_alt = sum(1 for img in images if not (img.get("alt") or "").strip())

        # Internal links
        internal_links = []
        for a in soup.find_all("a", href=True):
            nu = normalize_url(final_url, a["href"])
            if nu and same_domain(nu, self.root_domain):
                internal_links.append({"url": nu, "text": a.get_text(strip=True)[:120]})

        text = soup.get_text(" ", strip=True)
        words = re.findall(r"\w+", text)
        word_count = len(words)

        indexable = True
        if robots_meta and ("noindex" in robots_meta):
            indexable = False
        if status >= 400:
            indexable = False

        return {
            "url": url,
            "final_url": final_url,
            "status_code": status,
            "title": title,
            "meta_description": meta_desc,
            "h1": h1s[0] if h1s else None,
            "headings": {"h1": h1s, "h2": h2s, "h3": h3s},
            "canonical_url": canonical,
            "is_canonical": (canonical is None) or (normalize_url(url, canonical or "") == normalize_url(url, url)),
            "is_indexable": indexable,
            "robots_meta": robots_meta,
            "has_structured_data": len(structured) > 0,
            "structured_data": structured[:10],
            "open_graph": og or None,
            "twitter_card": tw or None,
            "word_count": word_count,
            "is_thin_content": word_count < 150,
            "images_total": len(images),
            "images_missing_alt": missing_alt,
            "internal_links": internal_links[:200],
            "page_size_bytes": len(html.encode("utf-8", errors="ignore")),
        }

    async def crawl(self) -> dict[str, Any]:
        headers = {"User-Agent": settings.user_agent}
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=headers,
        ) as client:
            await self._progress("robots", 5, "Fetching robots.txt")
            await self.fetch_robots(client)

            await self._progress("sitemap", 10, "Discovering sitemaps")
            await self.fetch_sitemaps(client)

            # Seed queue: start URL + sitemap URLs
            queue: deque[tuple[str, int]] = deque()
            queue.append((self.start_url, 0))
            for su in self.sitemap_urls:
                if same_domain(su, self.root_domain):
                    queue.append((su, 0))

            await self._progress("crawl", 15, f"Starting crawl (max {self.max_pages} pages)")

            while queue and len(self.pages) < self.max_pages:
                url, depth = queue.popleft()
                if url in self.visited:
                    continue
                if depth > self.max_depth:
                    continue
                if not self.is_allowed(url):
                    continue

                self.visited.add(url)
                try:
                    # SSRF check for every URL
                    safe = validate_url_for_crawl(url)
                    resp = await client.get(safe)
                    final = str(resp.url)
                    content_type = resp.headers.get("content-type", "")
                    if "text/html" not in content_type and "application/xhtml" not in content_type:
                        continue

                    page_data = self.parse_page(url, resp.status_code, resp.text, final)
                    page_data["depth"] = depth
                    self.pages.append(page_data)

                    # Enqueue internal links
                    if depth < self.max_depth:
                        for link in page_data.get("internal_links", []):
                            nu = link["url"]
                            if nu not in self.visited:
                                queue.append((nu, depth + 1))

                    pct = 15 + int(70 * len(self.pages) / self.max_pages)
                    await self._progress(
                        "crawl",
                        min(pct, 85),
                        f"Crawled {len(self.pages)} pages",
                        pages_crawled=len(self.pages),
                        pages_discovered=len(self.visited) + len(queue),
                    )
                    if self.delay:
                        await asyncio.sleep(self.delay)
                except SSRFError:
                    continue
                except Exception as e:
                    self.pages.append({
                        "url": url,
                        "status_code": 0,
                        "error": str(e),
                        "depth": depth,
                        "is_indexable": False,
                    })

            await self._progress("done", 90, f"Crawl finished: {len(self.pages)} pages")

        return {
            "start_url": self.start_url,
            "domain": self.root_domain,
            "pages": self.pages,
            "robots_txt": self.robots_txt,
            "sitemap_urls": list(set(self.sitemap_urls)),
            "pages_crawled": len(self.pages),
            "pages_discovered": len(self.visited),
        }
