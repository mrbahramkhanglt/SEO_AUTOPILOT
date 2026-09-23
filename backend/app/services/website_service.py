"""Website validation and basic discovery (PHASE 1)."""
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.security.ssrf import SSRFError, validate_url_for_crawl

settings = get_settings()


async def validate_and_discover_website(url: str) -> dict[str, Any]:
    """
    Quick validation + discovery of robots.txt, sitemap, and technology hints.
    Does not perform a full crawl (that is PHASE 2).
    """
    result: dict[str, Any] = {
        "is_valid": False,
        "error": None,
        "has_robots": False,
        "has_sitemap": False,
        "robots_url": None,
        "sitemap_url": None,
        "technology_stack": {},
        "final_url": None,
        "status_code": None,
    }

    try:
        safe_url = validate_url_for_crawl(url)
    except SSRFError as e:
        result["error"] = str(e)
        return result

    headers = {"User-Agent": settings.user_agent}

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=settings.crawl_timeout_seconds,
        headers=headers,
    ) as client:
        # 1. Fetch homepage
        try:
            resp = await client.get(safe_url)
            result["status_code"] = resp.status_code
            result["final_url"] = str(resp.url)

            if resp.status_code >= 400:
                result["error"] = f"HTTP {resp.status_code}"
                return result

            result["is_valid"] = True
            html = resp.text
            soup = BeautifulSoup(html, "lxml")

            # Basic tech detection
            tech: dict[str, Any] = {}
            generator = soup.find("meta", attrs={"name": "generator"})
            if generator and generator.get("content"):
                tech["generator"] = generator["content"]

            # Framework hints
            scripts = [s.get("src", "") for s in soup.find_all("script", src=True)]
            if any("react" in s.lower() or "_next" in s.lower() for s in scripts):
                tech["framework"] = "Next.js / React"
            elif any("vue" in s.lower() or "nuxt" in s.lower() for s in scripts):
                tech["framework"] = "Vue / Nuxt"
            elif any("angular" in s.lower() for s in scripts):
                tech["framework"] = "Angular"

            # WordPress
            if any("wp-content" in s or "wp-includes" in s for s in scripts) or soup.find(
                "link", href=lambda h: h and "wp-content" in h
            ):
                tech["cms"] = "WordPress"

            # Shopify
            if any("cdn.shopify.com" in s for s in scripts):
                tech["platform"] = "Shopify"

            result["technology_stack"] = tech

        except httpx.HTTPError as e:
            result["error"] = f"Connection error: {e}"
            return result

        # 2. robots.txt
        base = f"{urlparse(str(resp.url)).scheme}://{urlparse(str(resp.url)).netloc}"
        robots_url = urljoin(base, "/robots.txt")
        try:
            r = await client.get(robots_url)
            if r.status_code == 200 and "user-agent" in r.text.lower():
                result["has_robots"] = True
                result["robots_url"] = robots_url
                # Look for sitemap directives
                for line in r.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        result["has_sitemap"] = True
                        result["sitemap_url"] = line.split(":", 1)[1].strip()
                        break
        except httpx.HTTPError:
            pass

        # 3. Common sitemap locations if not found in robots
        if not result["has_sitemap"]:
            candidates = [
                "/sitemap.xml",
                "/sitemap_index.xml",
                "/sitemap-index.xml",
                "/sitemaps.xml",
            ]
            for path in candidates:
                try:
                    s = await client.get(urljoin(base, path))
                    if s.status_code == 200 and ("<urlset" in s.text or "<sitemapindex" in s.text):
                        result["has_sitemap"] = True
                        result["sitemap_url"] = urljoin(base, path)
                        break
                except httpx.HTTPError:
                    continue

    return result
