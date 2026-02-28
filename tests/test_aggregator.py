"""Tests for the aggregator service."""

from __future__ import annotations

from unittest.mock import AsyncMock

from dashboard.models import DashboardConfig, FlyOrgConfig, OrgConfig, RepoConfig
from dashboard.services.aggregator import Aggregator


def make_github_mock(
    repos=None,
    branches=None,
    comparison=None,
    codespaces=None,
    commit_count=0,
):
    """Create a mock GitHubClient with preset responses."""
    gh = AsyncMock()
    gh.list_org_repos.return_value = repos or []
    gh.list_branches.return_value = branches or []
    gh.compare_branches.return_value = comparison or {"ahead_by": 0, "behind_by": 0}
    gh.list_codespaces.return_value = codespaces or []
    gh.get_commit_count.return_value = commit_count
    return gh


def make_fly_mock(apps=None, machines=None):
    """Create a mock FlyClient with preset responses."""
    fly = AsyncMock()
    fly.list_apps.return_value = apps or []
    fly.list_machines.return_value = machines or []
    return fly


class TestSingleRepo:
    async def test_basic_repo(self):
        gh = make_github_mock(
            repos=[
                {
                    "name": "my-repo",
                    "full_name": "org/my-repo",
                    "description": "A repo",
                    "html_url": "https://github.com/org/my-repo",
                    "default_branch": "main",
                    "language": "Python",
                    "updated_at": "2025-01-15T10:30:00Z",
                }
            ],
            branches=[{"name": "main"}],
        )
        config = DashboardConfig(github_orgs=[OrgConfig(name="org", include_all=True)])

        agg = Aggregator(config, gh)
        data = await agg.build()

        assert len(data.repos) == 1
        assert data.repos[0].repo.name == "my-repo"
        assert data.repos[0].repo.org == "org"
        assert data.repos[0].repo.language == "Python"
        assert data.errors == []


class TestDefaultBranchMarking:
    async def test_marks_default_branch(self):
        gh = make_github_mock(
            repos=[{"name": "r", "full_name": "o/r", "default_branch": "main"}],
            branches=[{"name": "main"}, {"name": "develop"}],
        )
        config = DashboardConfig(github_orgs=[OrgConfig(name="o", include_all=True)])

        agg = Aggregator(config, gh)
        data = await agg.build()

        branches = data.repos[0].repo.branches
        assert len(branches) == 2
        main_branch = next(b for b in branches if b.name == "main")
        dev_branch = next(b for b in branches if b.name == "develop")
        assert main_branch.is_default is True
        assert dev_branch.is_default is False


class TestCodespaceCounts:
    async def test_counts_codespaces(self):
        gh = make_github_mock(
            repos=[{"name": "r", "full_name": "o/r", "default_branch": "main"}],
            codespaces=[
                {"name": "cs1", "state": "Available", "owner": {"login": "user1"}},
                {"name": "cs2", "state": "Shutdown", "owner": {"login": "user2"}},
            ],
        )
        config = DashboardConfig(github_orgs=[OrgConfig(name="o", include_all=True)])

        agg = Aggregator(config, gh)
        data = await agg.build()

        repo = data.repos[0].repo
        assert repo.codespace_count == 2
        assert len(repo.codespaces) == 2
        assert repo.codespaces[0].owner == "user1"


class TestCommitCountAndPushedAt:
    async def test_passes_commit_count_and_pushed_at(self):
        gh = make_github_mock(
            repos=[
                {
                    "name": "r",
                    "full_name": "o/r",
                    "default_branch": "main",
                    "pushed_at": "2025-03-01T12:00:00Z",
                }
            ],
            commit_count=42,
        )
        config = DashboardConfig(github_orgs=[OrgConfig(name="o", include_all=True)])

        agg = Aggregator(config, gh)
        data = await agg.build()

        repo = data.repos[0].repo
        assert repo.commit_count == 42
        assert repo.pushed_at is not None
        assert repo.pushed_at.year == 2025

    async def test_commit_count_error_non_fatal(self):
        gh = make_github_mock(
            repos=[{"name": "r", "full_name": "o/r", "default_branch": "main"}],
        )
        gh.get_commit_count.side_effect = Exception("rate limited")

        config = DashboardConfig(github_orgs=[OrgConfig(name="o")])

        agg = Aggregator(config, gh)
        data = await agg.build()

        assert len(data.repos) == 1
        assert data.repos[0].repo.commit_count == 0
        assert any("Commit count" in e for e in data.errors)


class TestIncludeAllBehavior:
    async def test_include_all_true(self):
        gh = make_github_mock(
            repos=[
                {"name": "repo1", "full_name": "o/repo1", "default_branch": "main"},
                {"name": "repo2", "full_name": "o/repo2", "default_branch": "main"},
            ]
        )
        config = DashboardConfig(github_orgs=[OrgConfig(name="o", include_all=True)])

        agg = Aggregator(config, gh)
        data = await agg.build()
        assert len(data.repos) == 2

    async def test_include_all_false(self):
        gh = make_github_mock(
            repos=[
                {"name": "repo1", "full_name": "o/repo1", "default_branch": "main"},
                {"name": "repo2", "full_name": "o/repo2", "default_branch": "main"},
                {"name": "repo3", "full_name": "o/repo3", "default_branch": "main"},
            ]
        )
        config = DashboardConfig(
            github_orgs=[
                OrgConfig(
                    name="o",
                    include_all=False,
                    repos=[RepoConfig(name="repo1"), RepoConfig(name="repo3")],
                )
            ]
        )

        agg = Aggregator(config, gh)
        data = await agg.build()
        assert len(data.repos) == 2
        names = {r.repo.name for r in data.repos}
        assert names == {"repo1", "repo3"}


class TestCategoryAndTags:
    async def test_applies_overrides(self):
        gh = make_github_mock(
            repos=[{"name": "web", "full_name": "o/web", "default_branch": "main"}],
        )
        config = DashboardConfig(
            github_orgs=[
                OrgConfig(
                    name="o",
                    repos=[RepoConfig(name="web", category="Frontend", tags=["prod"])],
                )
            ]
        )

        agg = Aggregator(config, gh)
        data = await agg.build()
        assert data.repos[0].repo.category == "Frontend"
        assert data.repos[0].repo.tags == ["prod"]

    async def test_defaults_without_override(self):
        gh = make_github_mock(
            repos=[{"name": "other", "full_name": "o/other", "default_branch": "main"}],
        )
        config = DashboardConfig(github_orgs=[OrgConfig(name="o")])

        agg = Aggregator(config, gh)
        data = await agg.build()
        assert data.repos[0].repo.category == "Uncategorized"
        assert data.repos[0].repo.tags == []


class TestFlyIntegration:
    async def test_attaches_fly_app(self):
        gh = make_github_mock(
            repos=[{"name": "web", "full_name": "o/web", "default_branch": "main"}],
        )
        fly = make_fly_mock(
            apps=[{"name": "web-prod", "status": "deployed", "hostname": "web-prod.fly.dev"}],
            machines=[{"id": "m1", "name": "web", "state": "started", "region": "iad"}],
        )
        config = DashboardConfig(
            github_orgs=[
                OrgConfig(
                    name="o",
                    repos=[RepoConfig(name="web", fly_app="web-prod")],
                )
            ],
            fly_orgs=[FlyOrgConfig(slug="my-fly")],
        )

        agg = Aggregator(config, gh, fly)
        data = await agg.build()
        assert data.repos[0].fly_app is not None
        assert data.repos[0].fly_app.name == "web-prod"
        assert len(data.repos[0].fly_app.machines) == 1

    async def test_no_fly_token(self):
        gh = make_github_mock(
            repos=[{"name": "r", "full_name": "o/r", "default_branch": "main"}],
        )
        config = DashboardConfig(
            github_orgs=[OrgConfig(name="o")],
            fly_orgs=[FlyOrgConfig(slug="my-fly")],
        )

        agg = Aggregator(config, gh, fly=None)
        data = await agg.build()
        assert data.repos[0].fly_app is None
        assert data.errors == []


class TestErrorHandling:
    async def test_github_org_error(self):
        gh = make_github_mock()
        gh.list_org_repos.side_effect = Exception("API rate limited")
        config = DashboardConfig(github_orgs=[OrgConfig(name="o")])

        agg = Aggregator(config, gh)
        data = await agg.build()
        assert len(data.repos) == 0
        assert any("rate limited" in e for e in data.errors)

    async def test_branch_fetch_error_non_fatal(self):
        gh = make_github_mock(
            repos=[{"name": "r", "full_name": "o/r", "default_branch": "main"}],
        )
        gh.list_branches.side_effect = Exception("timeout")

        config = DashboardConfig(github_orgs=[OrgConfig(name="o")])

        agg = Aggregator(config, gh)
        data = await agg.build()
        # Repo should still appear, just without branch data
        assert len(data.repos) == 1
        assert data.repos[0].repo.branches == []
        assert any("timeout" in e for e in data.errors)

    async def test_fly_org_error(self):
        gh = make_github_mock(
            repos=[{"name": "r", "full_name": "o/r", "default_branch": "main"}],
        )
        fly = make_fly_mock()
        fly.list_apps.side_effect = Exception("Fly auth failed")

        config = DashboardConfig(
            github_orgs=[OrgConfig(name="o")],
            fly_orgs=[FlyOrgConfig(slug="bad-org")],
        )

        agg = Aggregator(config, gh, fly)
        data = await agg.build()
        assert len(data.repos) == 1
        assert any("Fly" in e for e in data.errors)
