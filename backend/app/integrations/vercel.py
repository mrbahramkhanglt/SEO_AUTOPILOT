"""Vercel integration – list projects, trigger deployment, inspect."""
from __future__ import annotations

from typing import Any, Optional

import httpx

VERCEL_API = "https://api.vercel.com"


class VercelIntegration:
    def __init__(self, access_token: Optional[str] = None, team_id: Optional[str] = None):
        self.token = access_token
        self.team_id = team_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _params(self) -> dict[str, str]:
        return {"teamId": self.team_id} if self.team_id else {}

    async def list_projects(self) -> list[dict[str, Any]]:
        if not self.token:
            raise RuntimeError("Vercel token required")
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{VERCEL_API}/v9/projects",
                headers=self._headers(),
                params=self._params(),
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            projects = data.get("projects") or data if isinstance(data, list) else data.get("projects") or []
            return [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "framework": p.get("framework"),
                    "updated_at": p.get("updatedAt"),
                }
                for p in projects
            ]

    async def list_deployments(self, project_id: str, limit: int = 5) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            params = {**self._params(), "projectId": project_id, "limit": limit}
            r = await client.get(
                f"{VERCEL_API}/v6/deployments",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            deps = (r.json() or {}).get("deployments") or []
            return [
                {
                    "uid": d.get("uid"),
                    "url": d.get("url"),
                    "state": d.get("state") or d.get("readyState"),
                    "created": d.get("created"),
                }
                for d in deps
            ]

    async def get_deployment(self, deployment_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{VERCEL_API}/v13/deployments/{deployment_id}",
                headers=self._headers(),
                params=self._params(),
                timeout=20,
            )
            r.raise_for_status()
            d = r.json()
            return {
                "uid": d.get("uid") or d.get("id"),
                "url": d.get("url"),
                "readyState": d.get("readyState"),
                "alias": d.get("alias"),
            }
