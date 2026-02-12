"""Tests for API key auth dependency."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from dashboard.auth import require_api_key

API_KEY = "test-secret-key"


@pytest.fixture
def app():
    app = FastAPI()

    @app.get("/protected")
    def protected(key: str = Depends(require_api_key)):
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestAuth:
    def test_valid_query_param(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_API_KEY", API_KEY)
        resp = client.get("/protected", params={"api_key": API_KEY})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_valid_header(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_API_KEY", API_KEY)
        resp = client.get("/protected", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200

    def test_missing_key_returns_401(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_API_KEY", API_KEY)
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "required" in resp.json()["detail"].lower()

    def test_invalid_key_returns_403(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_API_KEY", API_KEY)
        resp = client.get("/protected", params={"api_key": "wrong-key"})
        assert resp.status_code == 403
        assert "invalid" in resp.json()["detail"].lower()

    def test_missing_env_returns_500(self, client, monkeypatch):
        monkeypatch.delenv("DASHBOARD_API_KEY", raising=False)
        resp = client.get("/protected", params={"api_key": "anything"})
        assert resp.status_code == 500
        assert "not configured" in resp.json()["detail"].lower()

    def test_header_takes_precedence_over_missing_query(self, client, monkeypatch):
        monkeypatch.setenv("DASHBOARD_API_KEY", API_KEY)
        resp = client.get("/protected", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200
