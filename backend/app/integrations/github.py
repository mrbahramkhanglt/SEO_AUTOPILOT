"""GitHub integration – OAuth, repo access, SEO branch + PR workflow."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

settings = get_settings()

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"


class GitHubIntegration:
    """
    Production flow:
    1. OAuth connect
    2. List repos / select repo
    3. Create branch seo-autopilot/optimize-YYYY-MM-DD
    4. Commit safe SEO files (metadata helpers, schema JSON, sitemap, robots)
    5. Open pull request – never force-push to main
    6. Optional: wait for checks, merge only if settings allow
    """

    def __init__(self, access_token: Optional[str] = None):
        self.token = access_token
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "repo read:user",
            "state": state,
        }
        return f"{GITHUB_AUTHORIZE}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                GITHUB_TOKEN,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=20,
            )
            r.raise_for_status()
            return r.json()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def list_repos(self, per_page: int = 50) -> list[dict[str, Any]]:
        if not self.token:
            raise RuntimeError("GitHub token required")
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}/user/repos",
                headers=self._headers(),
                params={"per_page": per_page, "sort": "updated"},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}",
                headers=self._headers(),
                timeout=20,
            )
            r.raise_for_status()
            return r.json()

    async def create_seo_branch(self, owner: str, repo: str, from_branch: str = "main") -> dict[str, Any]:
        """Create branch seo-autopilot/optimize-YYYY-MM-DD from base ref."""
        branch_name = f"seo-autopilot/optimize-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        async with httpx.AsyncClient() as client:
            # Get base SHA
            ref_r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{from_branch}",
                headers=self._headers(),
                timeout=20,
            )
            if ref_r.status_code == 404:
                # try master
                ref_r = await client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/master",
                    headers=self._headers(),
                    timeout=20,
                )
                from_branch = "master"
            ref_r.raise_for_status()
            sha = ref_r.json()["object"]["sha"]

            # Create branch ref
            create = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/refs",
                headers=self._headers(),
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
                timeout=20,
            )
            if create.status_code == 422:
                # branch may already exist
                return {"branch": branch_name, "sha": sha, "existed": True}
            create.raise_for_status()
            return {"branch": branch_name, "sha": sha, "existed": False, "base": from_branch}

    async def commit_files(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: dict[str, str],
        message: str = "SEO Autopilot: optimize metadata, sitemap and structured data",
    ) -> dict[str, Any]:
        """
        Commit multiple text files to a branch using the Contents API (simple path).
        files: path -> content
        """
        import base64

        results = []
        async with httpx.AsyncClient() as client:
            for path, content in files.items():
                # Get existing file sha if present
                get_r = await client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                    headers=self._headers(),
                    params={"ref": branch},
                    timeout=20,
                )
                payload: dict[str, Any] = {
                    "message": message,
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "branch": branch,
                }
                if get_r.status_code == 200:
                    payload["sha"] = get_r.json()["sha"]

                put_r = await client.put(
                    f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                    headers=self._headers(),
                    json=payload,
                    timeout=30,
                )
                put_r.raise_for_status()
                results.append({"path": path, "status": put_r.status_code})

        return {"committed": results, "branch": branch, "message": message}

    async def open_pull_request(
        self,
        owner: str,
        repo: str,
        head_branch: str,
        base_branch: str = "main",
        title: str = "SEO Autopilot: safe SEO optimizations",
        body: str = "",
    ) -> dict[str, Any]:
        if not body:
            body = (
                "## SEO Autopilot AI\n\n"
                "This PR contains **safe, non-destructive** SEO improvements:\n"
                "- Metadata / schema / sitemap / robots suggestions\n\n"
                "**Review required** before merge. "
                "SEO Autopilot never force-pushes to production branches.\n\n"
                "_Potential SEO improvement only — rankings are not guaranteed._"
            )
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                headers=self._headers(),
                json={
                    "title": title,
                    "head": head_branch,
                    "base": base_branch,
                    "body": body,
                },
                timeout=30,
            )
            if r.status_code == 422:
                return {"error": r.json(), "message": "PR may already exist"}
            r.raise_for_status()
            data = r.json()
            return {
                "number": data.get("number"),
                "html_url": data.get("html_url"),
                "state": data.get("state"),
            }

    def build_seo_files_from_autofix(self, autofix: dict[str, Any]) -> dict[str, str]:
        """Map autofix artifacts to repo paths (static-site friendly)."""
        files: dict[str, str] = {}
        if autofix.get("robots_txt_full") or autofix.get("robots_txt"):
            files["public/robots.txt"] = autofix.get("robots_txt_full") or autofix.get("robots_txt")
        sitemap = autofix.get("sitemap_xml_full") or autofix.get("sitemap_xml_preview")
        if sitemap:
            files["public/sitemap.xml"] = sitemap
        # Schema and metadata as reviewable JSON under seo-autopilot/
        meta = autofix.get("metadata_fixes") or []
        if meta:
            import json
            files["seo-autopilot/metadata-fixes.json"] = json.dumps(meta, indent=2, ensure_ascii=False)
        schemas = autofix.get("schema_blocks") or []
        if schemas:
            import json
            files["seo-autopilot/schema-blocks.json"] = json.dumps(schemas, indent=2, ensure_ascii=False)
        return files
