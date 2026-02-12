"""Tests for the JSON API route."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from dashboard.app import create_app
from dashboard.auth import require_api_key
from dashboard.dependencies import get_aggregator
from dashboard.models import DashboardData, RepoData, RepoView
from dashboard.services.aggregator import Aggregator

API_KEY = "test-key"


def _write_minimal_config(tmp_path: Path) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text("github_orgs: []")
    return p


def make_test_app(tmp_path: Path, dashboard_data: DashboardData | None = None):
    """Create a test app with mocked aggregator."""
    config_path = _write_minimal_config(tmp_path)
    app = create_app(config_path)

    # Override auth
    app.dependency_overrides[require_api_key] = lambda: API_KEY

    # Override aggregator
    if dashboard_data is not None:
        mock_agg = AsyncMock(spec=Aggregator)
        mock_agg.build.return_value = dashboard_data
        app.dependency_overrides[get_aggregator] = lambda: mock_agg

    return app


class TestApiDashboard:
    def test_returns_json(self, tmp_path):
        data = DashboardData(
            repos=[
                RepoView(repo=RepoData(org="o", name="r", full_name="o/r")),
            ],
            errors=[],
        )
        app = make_test_app(tmp_path, data)
        client = TestClient(app)

        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["repos"]) == 1
        assert body["repos"][0]["repo"]["name"] == "r"
        assert body["errors"] == []

    def test_response_structure(self, tmp_path):
        data = DashboardData()
        app = make_test_app(tmp_path, data)
        client = TestClient(app)

        resp = client.get("/api/dashboard")
        body = resp.json()
        assert "repos" in body
        assert "errors" in body
        assert "generated_at" in body

    def test_requires_auth(self, tmp_path):
        """Without the auth override, missing key should fail."""
        config_path = _write_minimal_config(tmp_path)
        app = create_app(config_path)
        # Don't override auth — let it check for real
        mock_agg = AsyncMock(spec=Aggregator)
        mock_agg.build.return_value = DashboardData()
        app.dependency_overrides[get_aggregator] = lambda: mock_agg

        client = TestClient(app)
        resp = client.get("/api/dashboard")
        # Should fail because DASHBOARD_API_KEY isn't set (or is wrong)
        assert resp.status_code in (401, 500)
