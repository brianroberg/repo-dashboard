"""Tests for GitHub REST API client."""

from __future__ import annotations

import httpx
import pytest

from dashboard.clients.github import GitHubClient

TOKEN = "ghp_test_token"


def make_response(data, status_code=200, headers=None):
    """Create an httpx.Response with JSON body."""
    return httpx.Response(
        status_code=status_code,
        json=data,
        headers=headers or {},
    )


def mock_transport(handler):
    """Create an httpx.MockTransport from a request handler."""
    return httpx.MockTransport(handler)


@pytest.fixture
def make_client():
    """Factory to create GitHubClient with a mock transport."""

    def _make(handler):
        transport = mock_transport(handler)
        http = httpx.AsyncClient(transport=transport)
        return GitHubClient(http, TOKEN)

    return _make


class TestAuthHeader:
    async def test_sends_auth_header(self, make_client):
        captured_headers = {}

        def handler(request: httpx.Request):
            captured_headers.update(dict(request.headers))
            return make_response([])

        client = make_client(handler)
        await client.list_org_repos("test-org")
        assert captured_headers["authorization"] == f"token {TOKEN}"
        assert "github" in captured_headers["accept"]


class TestListOrgRepos:
    async def test_returns_repos(self, make_client):
        repos = [{"name": "repo1", "full_name": "org/repo1"}]

        def handler(request: httpx.Request):
            return make_response(repos)

        client = make_client(handler)
        result = await client.list_org_repos("org")
        assert len(result) == 1
        assert result[0]["name"] == "repo1"

    async def test_pagination(self, make_client):
        page1 = [{"name": f"repo{i}"} for i in range(100)]
        page2 = [{"name": "repo100"}]

        def handler(request: httpx.Request):
            url = str(request.url)
            if "page=2" in url:
                return make_response(page2)
            return make_response(
                page1,
                headers={"Link": '<https://api.github.com/orgs/org/repos?page=2>; rel="next"'},
            )

        client = make_client(handler)
        result = await client.list_org_repos("org")
        assert len(result) == 101


class TestListBranches:
    async def test_returns_branches(self, make_client):
        branches = [{"name": "main"}, {"name": "develop"}]

        def handler(request: httpx.Request):
            return make_response(branches)

        client = make_client(handler)
        result = await client.list_branches("org", "repo")
        assert len(result) == 2
        assert result[0]["name"] == "main"


class TestCompareBranches:
    async def test_returns_comparison(self, make_client):
        comparison = {"ahead_by": 3, "behind_by": 1, "status": "ahead"}

        def handler(request: httpx.Request):
            assert "/compare/main...feature" in str(request.url)
            return make_response(comparison)

        client = make_client(handler)
        result = await client.compare_branches("org", "repo", "main", "feature")
        assert result["ahead_by"] == 3
        assert result["behind_by"] == 1


class TestListCodespaces:
    async def test_returns_codespaces(self, make_client):
        def handler(request: httpx.Request):
            assert "/codespaces" in str(request.url)
            return make_response(
                {
                    "total_count": 2,
                    "codespaces": [
                        {"name": "cs1", "state": "Available"},
                        {"name": "cs2", "state": "Shutdown"},
                    ],
                }
            )

        client = make_client(handler)
        result = await client.list_codespaces("org", "repo")
        assert len(result) == 2
        assert result[0]["name"] == "cs1"

    async def test_empty_codespaces(self, make_client):
        def handler(request: httpx.Request):
            return make_response({"total_count": 0, "codespaces": []})

        client = make_client(handler)
        result = await client.list_codespaces("org", "repo")
        assert result == []


class TestParseNextLink:
    def test_with_next(self):
        header = (
            '<https://api.github.com/orgs/org/repos?page=2>; rel="next", '
            '<https://api.github.com/orgs/org/repos?page=5>; rel="last"'
        )
        url = GitHubClient._parse_next_link(header)
        assert url == "https://api.github.com/orgs/org/repos?page=2"

    def test_without_next(self):
        header = '<https://api.github.com/orgs/org/repos?page=5>; rel="last"'
        assert GitHubClient._parse_next_link(header) is None

    def test_empty(self):
        assert GitHubClient._parse_next_link("") is None
