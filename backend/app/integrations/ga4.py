"""Google Analytics 4 integration scaffold."""
from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

settings = get_settings()

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GA4_DATA = "https://analyticsdata.googleapis.com/v1beta"
SCOPES = "https://www.googleapis.com/auth/analytics.readonly"


class GA4Integration:
    """
    Analyze organic traffic, landing pages, engagement, conversions.
    Connect SEO work to business outcomes — without over-claiming causality.
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
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

    async def run_report(
        self,
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "yesterday",
    ) -> dict[str, Any]:
        if not self.access_token:
            raise RuntimeError("GA4 access token required")
        body = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}, {"name": "landingPage"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "engagedSessions"},
                {"name": "conversions"},
            ],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "sessionDefaultChannelGroup",
                    "stringFilter": {"value": "Organic Search"},
                }
            },
            "limit": 50,
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GA4_DATA}/properties/{property_id}:runReport",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=body,
                timeout=40,
            )
            r.raise_for_status()
            data = r.json()
            return {
                "row_count": len(data.get("rows") or []),
                "rows": data.get("rows") or [],
                "note": "Organic landing page performance for correlating SEO changes with traffic.",
            }
