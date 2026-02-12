"""Fly.io Machines API client."""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://api.machines.dev"


class FlyClient:
    def __init__(self, http: httpx.AsyncClient, token: str) -> None:
        self._http = http
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        resp = await self._http.get(url, headers=self._headers, params=params)
        resp.raise_for_status()
        return resp

    async def list_apps(self, org_slug: str) -> list[dict[str, Any]]:
        """List all apps in a Fly.io org."""
        resp = await self._get(f"{BASE_URL}/v1/apps", params={"org_slug": org_slug})
        data = resp.json()
        return data.get("apps", data) if isinstance(data, dict) else data

    async def get_app(self, app_name: str) -> dict[str, Any]:
        """Get details for a specific app."""
        resp = await self._get(f"{BASE_URL}/v1/apps/{app_name}")
        return resp.json()

    async def list_machines(self, app_name: str) -> list[dict[str, Any]]:
        """List all machines for an app."""
        resp = await self._get(f"{BASE_URL}/v1/apps/{app_name}/machines")
        return resp.json()
