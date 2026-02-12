"""GitHub REST API client."""

from __future__ import annotations

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

    async def list_org_repos(self, org: str) -> list[dict[str, Any]]:
        """List all repositories for a GitHub org."""
        return await self._get_paginated(f"{BASE_URL}/orgs/{org}/repos", {"type": "all"})

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
