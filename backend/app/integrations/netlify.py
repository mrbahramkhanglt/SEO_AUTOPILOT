"""Netlify integration – list sites, trigger deploy, verify."""
from __future__ import annotations

from typing import Any, Optional

import httpx

NETLIFY_API = "https://api.netlify.com/api/v1"


class NetlifyIntegration:
    def __init__(self, access_token: Optional[str] = None):
        self.token = access_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def list_sites(self) -> list[dict[str, Any]]:
        if not self.token:
            raise RuntimeError("Netlify token required")
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{NETLIFY_API}/sites", headers=self._headers(), timeout=30)
            r.raise_for_status()
            sites = r.json()
            return [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "url": s.get("url") or s.get("ssl_url"),
                    "admin_url": s.get("admin_url"),
                    "published_deploy_id": (s.get("published_deploy") or {}).get("id"),
                }
                for s in sites
            ]

    async def get_site(self, site_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{NETLIFY_API}/sites/{site_id}", headers=self._headers(), timeout=20)
            r.raise_for_status()
            return r.json()

    async def trigger_build(self, site_id: str, clear_cache: bool = False) -> dict[str, Any]:
        """Trigger a new deploy/build for the site."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{NETLIFY_API}/sites/{site_id}/builds",
                headers=self._headers(),
                json={"clear_cache": clear_cache},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            return {
                "deploy_id": data.get("deploy_id") or data.get("id"),
                "state": data.get("state"),
                "message": "Build triggered. Monitor deploy status before verifying SEO changes.",
            }

    async def get_deploy(self, site_id: str, deploy_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{NETLIFY_API}/sites/{site_id}/deploys/{deploy_id}",
                headers=self._headers(),
                timeout=20,
            )
            r.raise_for_status()
            d = r.json()
            return {
                "id": d.get("id"),
                "state": d.get("state"),
                "error_message": d.get("error_message"),
                "ssl_url": d.get("ssl_url"),
                "published_at": d.get("published_at"),
            }
