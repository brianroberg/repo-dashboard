"""Tests for Fly.io Machines API client."""

from __future__ import annotations

import httpx
import pytest

from dashboard.clients.fly import FlyClient

TOKEN = "fly_test_token"


def make_response(data, status_code=200):
    return httpx.Response(status_code=status_code, json=data)


@pytest.fixture
def make_client():
    def _make(handler):
        transport = httpx.MockTransport(handler)
        http = httpx.AsyncClient(transport=transport)
        return FlyClient(http, TOKEN)

    return _make


class TestAuthHeader:
    async def test_sends_bearer_token(self, make_client):
        captured = {}

        def handler(request: httpx.Request):
            captured.update(dict(request.headers))
            return make_response({"apps": []})

        client = make_client(handler)
        await client.list_apps("my-org")
        assert captured["authorization"] == f"Bearer {TOKEN}"


class TestListApps:
    async def test_returns_apps(self, make_client):
        apps = [{"name": "app1", "status": "deployed"}, {"name": "app2", "status": "suspended"}]

        def handler(request: httpx.Request):
            assert "org_slug=my-org" in str(request.url)
            return make_response({"apps": apps})

        client = make_client(handler)
        result = await client.list_apps("my-org")
        assert len(result) == 2
        assert result[0]["name"] == "app1"

    async def test_returns_apps_from_list_response(self, make_client):
        """Some endpoints return a plain list instead of wrapped."""
        apps = [{"name": "app1"}]

        def handler(request: httpx.Request):
            return make_response(apps)

        client = make_client(handler)
        result = await client.list_apps("my-org")
        assert len(result) == 1


class TestGetApp:
    async def test_returns_app_details(self, make_client):
        app = {"name": "my-app", "status": "deployed", "hostname": "my-app.fly.dev"}

        def handler(request: httpx.Request):
            assert "/v1/apps/my-app" in str(request.url)
            return make_response(app)

        client = make_client(handler)
        result = await client.get_app("my-app")
        assert result["name"] == "my-app"
        assert result["hostname"] == "my-app.fly.dev"


class TestListMachines:
    async def test_returns_machines(self, make_client):
        machines = [
            {"id": "m1", "name": "web", "state": "started", "region": "iad"},
            {"id": "m2", "name": "worker", "state": "stopped", "region": "lax"},
        ]

        def handler(request: httpx.Request):
            assert "/machines" in str(request.url)
            return make_response(machines)

        client = make_client(handler)
        result = await client.list_machines("my-app")
        assert len(result) == 2
        assert result[0]["state"] == "started"
        assert result[1]["region"] == "lax"
