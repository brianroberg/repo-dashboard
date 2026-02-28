"""GitHub REST API client."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

BASE_URL = "https://api.github.com"


class GitHubClient:
    def __init__(self, http: httpx.AsyncClient, token: str) -> None:
        self._http = http
        self._headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }
        self._authenticated_user: str | None = None

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        resp = await self._http.get(url, headers=self._headers, params=params)
        resp.raise_for_status()
        return resp

    async def _get_paginated(self, url: str, params: dict[str, Any] | None = None) -> list[Any]:
        """Follow GitHub's Link header pagination to collect all pages."""
        results: list[Any] = []
        params = dict(params or {})
        params.setdefault("per_page", 100)

        next_url: str | None = url
        while next_url:
            resp = await self._get(next_url, params=params)
            results.extend(resp.json())
            next_url = self._parse_next_link(resp.headers.get("Link", ""))
            params = None  # params are included in the next URL

        return results

    @staticmethod
    def _parse_next_link(link_header: str) -> str | None:
        """Extract the 'next' URL from a GitHub Link header."""
        match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
        return match.group(1) if match else None

    async def _get_authenticated_user(self) -> str:
        """Return the login of the authenticated user (cached after first call)."""
        if self._authenticated_user is None:
            resp = await self._get(f"{BASE_URL}/user")
            self._authenticated_user = resp.json()["login"]
        return self._authenticated_user

    async def list_org_repos(self, org: str) -> list[dict[str, Any]]:
        """List all repositories for a GitHub org or user.

        Tries the /orgs endpoint first; if it 404s the name is a personal
        account.  For the authenticated user we hit /user/repos (includes
        private repos); for other users we fall back to /users/{name}/repos.
        """
        try:
            return await self._get_paginated(f"{BASE_URL}/orgs/{org}/repos", {"type": "all"})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            # Personal account — pick the right endpoint
            authed_user = await self._get_authenticated_user()
            if org.lower() == authed_user.lower():
                return await self._get_paginated(
                    f"{BASE_URL}/user/repos", {"type": "owner"}
                )
            return await self._get_paginated(
                f"{BASE_URL}/users/{org}/repos", {"type": "all"}
            )

    async def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List all branches for a repo."""
        return await self._get_paginated(f"{BASE_URL}/repos/{owner}/{repo}/branches")

    async def compare_branches(self, owner: str, repo: str, base: str, head: str) -> dict[str, Any]:
        """Compare two branches, returning ahead/behind counts."""
        resp = await self._get(f"{BASE_URL}/repos/{owner}/{repo}/compare/{base}...{head}")
        return resp.json()

    async def list_codespaces(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List codespaces for a repo."""
        resp = await self._get(f"{BASE_URL}/repos/{owner}/{repo}/codespaces")
        return resp.json().get("codespaces", [])

    async def get_commit_count(self, owner: str, repo: str) -> int:
        """Sum contributions across all contributors for total commit count.

        The contributors stats endpoint may return 202 while GitHub computes
        results.  We retry once after a short delay; on continued 202 or any
        error, return 0 so the caller degrades gracefully.

        Note: fetches only the first page (up to 100 contributors). Repos with
        more contributors will have an understated count, but this is used only
        as a sort signal so approximate ordering is acceptable.
        """
        url = f"{BASE_URL}/repos/{owner}/{repo}/contributors"
        for attempt in range(2):
            try:
                resp = await self._http.get(
                    url,
                    headers=self._headers,
                    params={"per_page": 100, "anon": "true"},
                )
                if resp.status_code == 202:
                    if attempt == 0:
                        await asyncio.sleep(1)
                        continue
                    return 0
                resp.raise_for_status()
                return sum(c.get("contributions", 0) for c in resp.json())
            except Exception:
                return 0
        return 0
