"""WordPress REST integration – Application Passwords, pages/posts, SEO meta dry-run/apply."""
from __future__ import annotations

import base64
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx

# SEO meta keys (Yoast + Rank Math) – writable only if site registered them for REST
YOAST_KEYS = {
    "title": "_yoast_wpseo_title",
    "description": "_yoast_wpseo_metadesc",
    "focus_kw": "_yoast_wpseo_focuskw",
    "canonical": "_yoast_wpseo_canonical",
}
RANK_MATH_KEYS = {
    "title": "rank_math_title",
    "description": "rank_math_description",
    "focus_kw": "rank_math_focus_keyword",
    "canonical": "rank_math_canonical_url",
}


class WordPressIntegration:
    """
    Secure WordPress SEO updates via Application Passwords + REST.
    Never overwrites without dry_run preview and optional conflict detection.
    Requires HTTPS (except localhost).
    """

    def __init__(
        self,
        site_url: str,
        username: str,
        app_password: str,
        seo_plugin: str = "auto",  # auto | yoast | rankmath
    ):
        self.base = site_url.rstrip("/")
        self.username = username
        # App passwords may include spaces – WordPress strips them
        self.app_password = app_password.replace(" ", "")
        self.seo_plugin = seo_plugin
        self._auth_header = self._basic_auth_header(username, self.app_password)

    @staticmethod
    def _basic_auth_header(username: str, password: str) -> str:
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {token}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _validate_url(self) -> None:
        parsed = urlparse(self.base)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("site_url must be http(s)")
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "http" and host not in ("localhost", "127.0.0.1"):
            raise ValueError("Application Passwords require HTTPS (except localhost)")

    async def test_connection(self) -> dict[str, Any]:
        self._validate_url()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base}/wp-json/wp/v2/users/me",
                headers=self._headers(),
                timeout=20,
            )
            if r.status_code == 401:
                raise RuntimeError("Authentication failed – check username / application password")
            r.raise_for_status()
            u = r.json()
            # Probe SEO plugins
            plugins = await self._detect_seo_surface(client)
            return {
                "ok": True,
                "id": u.get("id"),
                "name": u.get("name"),
                "slug": u.get("slug"),
                "roles": u.get("roles"),
                "seo": plugins,
            }

    async def _detect_seo_surface(self, client: httpx.AsyncClient) -> dict[str, Any]:
        out: dict[str, Any] = {
            "yoast_rest_head": False,
            "rank_math_graphql_hint": False,
            "wpgraphql": False,
            "meta_registration_unknown": True,
        }
        try:
            r = await client.get(f"{self.base}/wp-json/yoast/v1/get_head", params={"url": self.base}, timeout=10)
            out["yoast_rest_head"] = r.status_code < 500
        except Exception:
            pass
        try:
            r = await client.get(f"{self.base}/wp-json", timeout=10)
            if r.status_code == 200:
                ns = (r.json() or {}).get("namespaces") or []
                out["wpgraphql"] = "graphql" in str(ns).lower() or any("graphql" in str(n) for n in ns)
        except Exception:
            pass
        # GraphQL endpoint probe
        try:
            r = await client.post(
                f"{self.base}/graphql",
                json={"query": "{ __typename }"},
                timeout=8,
            )
            out["wpgraphql"] = out["wpgraphql"] or r.status_code in (200, 400)
        except Exception:
            pass
        return out

    async def list_content(
        self, content_type: str = "pages", per_page: int = 20, page: int = 1
    ) -> list[dict[str, Any]]:
        if content_type not in ("pages", "posts"):
            raise ValueError("content_type must be pages or posts")
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base}/wp-json/wp/v2/{content_type}",
                headers=self._headers(),
                params={"per_page": per_page, "page": page, "status": "publish", "context": "edit"},
                timeout=30,
            )
            r.raise_for_status()
            items = r.json()
            return [
                {
                    "id": p.get("id"),
                    "title": (p.get("title") or {}).get("rendered") or (p.get("title") or {}).get("raw"),
                    "link": p.get("link"),
                    "slug": p.get("slug"),
                    "type": content_type,
                    "meta": p.get("meta") or {},
                }
                for p in items
            ]

    async def get_item(self, content_type: str, item_id: int) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base}/wp-json/wp/v2/{content_type}/{item_id}",
                headers=self._headers(),
                params={"context": "edit"},
                timeout=20,
            )
            r.raise_for_status()
            p = r.json()
            return {
                "id": p.get("id"),
                "title": (p.get("title") or {}).get("rendered") or (p.get("title") or {}).get("raw"),
                "link": p.get("link"),
                "slug": p.get("slug"),
                "type": content_type,
                "meta": p.get("meta") or {},
            }

    def _meta_keys(self) -> dict[str, str]:
        if self.seo_plugin == "rankmath":
            return RANK_MATH_KEYS
        if self.seo_plugin == "yoast":
            return YOAST_KEYS
        # auto: prefer yoast keys; apply can send both if needed
        return YOAST_KEYS

    def build_meta_payload(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        focus_kw: Optional[str] = None,
        canonical: Optional[str] = None,
        include_rank_math: bool = False,
    ) -> dict[str, str]:
        keys = self._meta_keys()
        meta: dict[str, str] = {}
        mapping = {
            "title": title,
            "description": description,
            "focus_kw": focus_kw,
            "canonical": canonical,
        }
        for field, value in mapping.items():
            if value is not None and field in keys:
                meta[keys[field]] = value
        if include_rank_math or self.seo_plugin == "rankmath":
            for field, value in mapping.items():
                if value is not None and field in RANK_MATH_KEYS:
                    meta[RANK_MATH_KEYS[field]] = value
        return meta

    async def preview_meta_update(
        self,
        content_type: str,
        item_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        focus_kw: Optional[str] = None,
        canonical: Optional[str] = None,
    ) -> dict[str, Any]:
        """Read current meta and return proposed diff – no write."""
        current = await self.get_item(content_type, item_id)
        proposed = self.build_meta_payload(title, description, focus_kw, canonical, include_rank_math=True)
        cur_meta = current.get("meta") or {}
        conflicts = []
        for k, new_v in proposed.items():
            old_v = cur_meta.get(k)
            if old_v and str(old_v).strip() and str(old_v).strip() != str(new_v).strip():
                conflicts.append({"key": k, "current": old_v, "proposed": new_v})
        return {
            "status": "preview",
            "item": {"id": item_id, "type": content_type, "title": current.get("title"), "link": current.get("link")},
            "current_meta": {k: cur_meta.get(k) for k in proposed},
            "proposed_meta": proposed,
            "conflicts": conflicts,
            "message": (
                "Dry-run only. Apply requires dry_run=false and meta keys registered for REST "
                "(see docs/wordpress-meta-bridge.php)."
            ),
            "disclaimer": "Potential SEO improvement only — rankings are never guaranteed.",
        }

    async def apply_meta_update(
        self,
        content_type: str,
        item_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        focus_kw: Optional[str] = None,
        canonical: Optional[str] = None,
        dry_run: bool = True,
        force_overwrite: bool = False,
    ) -> dict[str, Any]:
        preview = await self.preview_meta_update(
            content_type, item_id, title, description, focus_kw, canonical
        )
        if dry_run:
            return preview
        if preview["conflicts"] and not force_overwrite:
            return {
                **preview,
                "status": "blocked",
                "message": "Conflicts detected. Set force_overwrite=true after review, or resolve manually.",
            }
        meta = preview["proposed_meta"]
        if not meta:
            return {**preview, "status": "noop", "message": "No meta fields to update"}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base}/wp-json/wp/v2/{content_type}/{item_id}",
                headers=self._headers(),
                json={"meta": meta},
                timeout=30,
            )
            if r.status_code >= 400:
                return {
                    **preview,
                    "status": "error",
                    "http_status": r.status_code,
                    "message": (
                        "Write failed. Ensure SEO meta keys are registered with show_in_rest "
                        f"(status {r.status_code}): {r.text[:300]}"
                    ),
                }
            data = r.json()
            return {
                **preview,
                "status": "applied",
                "saved_meta": (data.get("meta") or {}),
                "message": "Meta update request completed. Verify on site.",
                "disclaimer": "Potential SEO improvement only — rankings are never guaranteed.",
            }


class WPGraphQLClient:
    """Optional SEO read via WPGraphQL (Yoast/Rank Math schema if present)."""

    def __init__(self, site_url: str, username: Optional[str] = None, app_password: Optional[str] = None):
        self.endpoint = urljoin(site_url.rstrip("/") + "/", "graphql")
        self.username = username
        self.app_password = (app_password or "").replace(" ", "")

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.username and self.app_password:
            token = base64.b64encode(f"{self.username}:{self.app_password}".encode()).decode()
            h["Authorization"] = f"Basic {token}"
        return h

    async def query(self, query: str, variables: Optional[dict] = None) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self.endpoint,
                headers=self._headers(),
                json={"query": query, "variables": variables or {}},
                timeout=40,
            )
            r.raise_for_status()
            body = r.json()
            if body.get("errors"):
                raise RuntimeError(str(body["errors"][:3]))
            return body.get("data") or {}

    async def fetch_posts_seo(self, first: int = 10) -> dict[str, Any]:
        """Best-effort Yoast-style seo fields; fails if schema missing."""
        q = """
        query PostsSeo($first: Int!) {
          posts(first: $first) {
            nodes {
              databaseId
              title
              uri
              seo {
                title
                metaDesc
                canonical
                focuskw
              }
            }
          }
        }
        """
        try:
            return await self.query(q, {"first": first})
        except Exception as e:
            return {"error": str(e), "hint": "Install WPGraphQL + Yoast SEO GraphQL addon for this query."}
