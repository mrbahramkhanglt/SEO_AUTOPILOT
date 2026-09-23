"""Google Search Console integration scaffold (OAuth + read metrics)."""
from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

settings = get_settings()

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GSC_API = "https://www.googleapis.com/webmasters/v3"
SCOPES = "https://www.googleapis.com/auth/webmasters.readonly"


class GSCIntegration:
    """
    Reads:
    - search queries, impressions, clicks, CTR, position
    - indexed pages / coverage (via Search Analytics + sitemaps)
    Never writes spam. Used only to improve recommendations.
    """

    def __init__(self, access_token: Optional[str] = None, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                GOOGLE_TOKEN,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=20,
            )
            r.raise_for_status()
            return r.json()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def list_sites(self) -> list[dict[str, Any]]:
        if not self.access_token:
            raise RuntimeError("GSC access token required")
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GSC_API}/sites",
                headers=self._headers(),
                timeout=20,
            )
            r.raise_for_status()
            entries = (r.json() or {}).get("siteEntry") or []
            return [{"site_url": e.get("siteUrl"), "permission": e.get("permissionLevel")} for e in entries]

    async def search_analytics(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: list[str] | None = None,
        row_limit: int = 100,
    ) -> dict[str, Any]:
        """
        Fetch query/page performance.
        Identify: positions 4-20, high impressions low CTR, rising/declining.
        """
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions or ["query", "page"],
            "rowLimit": row_limit,
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GSC_API}/sites/{httpx.URL(site_url).raw_path.decode() if False else site_url.replace(':', '%3A').replace('/', '%2F')}/searchAnalytics/query",
                headers=self._headers(),
                json=body,
                timeout=40,
            )
            # Fallback encode
            if r.status_code >= 400:
                from urllib.parse import quote
                encoded = quote(site_url, safe="")
                r = await client.post(
                    f"{GSC_API}/sites/{encoded}/searchAnalytics/query",
                    headers=self._headers(),
                    json=body,
                    timeout=40,
                )
            r.raise_for_status()
            data = r.json()
            rows = data.get("rows") or []
            opportunities = []
            for row in rows:
                keys = row.get("keys") or []
                pos = row.get("position") or 100
                ctr = row.get("ctr") or 0
                impressions = row.get("impressions") or 0
                if 4 <= pos <= 20:
                    opportunities.append({
                        "type": "striking_distance",
                        "keys": keys,
                        "position": pos,
                        "ctr": ctr,
                        "impressions": impressions,
                        "clicks": row.get("clicks"),
                        "note": "Page/query in positions 4–20 — potential improvement zone.",
                    })
                elif impressions >= 50 and ctr < 0.02:
                    opportunities.append({
                        "type": "low_ctr",
                        "keys": keys,
                        "position": pos,
                        "ctr": ctr,
                        "impressions": impressions,
                        "note": "High impressions, low CTR — review title/meta.",
                    })
            return {
                "row_count": len(rows),
                "rows": rows[:50],
                "opportunities": opportunities[:30],
                "disclaimer": "Data informs recommendations only. Rankings are never guaranteed.",
            }
