"""Tests for the HTML dashboard route."""

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
    app.dependency_overrides[require_api_key] = lambda: API_KEY

    if dashboard_data is not None:
        mock_agg = AsyncMock(spec=Aggregator)
        mock_agg.build.return_value = dashboard_data
        app.dependency_overrides[get_aggregator] = lambda: mock_agg

    return app


class TestDashboardHtml:
    def test_returns_html(self, tmp_path):
        data = DashboardData(
            repos=[
                RepoView(
                    repo=RepoData(
                        org="my-org",
                        name="web-app",
                        full_name="my-org/web-app",
                        description="A web app",
                    )
                ),
            ],
        )
        app = make_test_app(tmp_path, data)
        client = TestClient(app)

        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_contains_repo_names(self, tmp_path):
        data = DashboardData(
            repos=[
                RepoView(repo=RepoData(org="o", name="repo-one", full_name="o/repo-one")),
                RepoView(repo=RepoData(org="o", name="repo-two", full_name="o/repo-two")),
            ],
        )
        app = make_test_app(tmp_path, data)
        client = TestClient(app)

        resp = client.get("/")
        html = resp.text
        assert "o/repo-one" in html
        assert "o/repo-two" in html

    def test_shows_errors(self, tmp_path):
        data = DashboardData(
            errors=["Failed to fetch org/bad-repo", "Fly auth error"],
        )
        app = make_test_app(tmp_path, data)
        client = TestClient(app)

        resp = client.get("/")
        html = resp.text
        assert "Failed to fetch org/bad-repo" in html
        assert "Fly auth error" in html

    def test_requires_auth(self, tmp_path):
        config_path = _write_minimal_config(tmp_path)
        app = create_app(config_path)
        mock_agg = AsyncMock(spec=Aggregator)
        mock_agg.build.return_value = DashboardData()
        app.dependency_overrides[get_aggregator] = lambda: mock_agg

        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code in (401, 500)

    def test_empty_state(self, tmp_path):
        data = DashboardData()
        app = make_test_app(tmp_path, data)
        client = TestClient(app)

        resp = client.get("/")
        html = resp.text
        assert "No repositories found" in html
