"""Tests for Pydantic data models."""

from __future__ import annotations

from datetime import datetime

from dashboard.models import (
    BranchInfo,
    CodespaceInfo,
    DashboardData,
    FlyAppInfo,
    FlyMachine,
    RepoData,
    RepoView,
)


class TestBranchInfo:
    def test_from_dict(self):
        b = BranchInfo(name="main", is_default=True)
        assert b.name == "main"
        assert b.is_default is True
        assert b.ahead == 0
        assert b.behind == 0

    def test_with_ahead_behind(self):
        b = BranchInfo(name="feature", ahead=3, behind=1)
        assert b.ahead == 3
        assert b.behind == 1
        assert b.is_default is False


class TestCodespaceInfo:
    def test_from_dict(self):
        c = CodespaceInfo(name="my-codespace", state="Available", owner="user1")
        assert c.name == "my-codespace"
        assert c.state == "Available"
        assert c.owner == "user1"

    def test_defaults(self):
        c = CodespaceInfo(name="cs", state="Shutdown")
        assert c.owner == ""


class TestRepoData:
    def test_minimal(self):
        r = RepoData(org="my-org", name="my-repo", full_name="my-org/my-repo")
        assert r.org == "my-org"
        assert r.name == "my-repo"
        assert r.category == "Uncategorized"
        assert r.tags == []
        assert r.branches == []
        assert r.codespaces == []
        assert r.codespace_count == 0
        assert r.default_branch == "main"
        assert r.description is None

    def test_full(self):
        r = RepoData(
            org="org",
            name="repo",
            full_name="org/repo",
            description="A repo",
            html_url="https://github.com/org/repo",
            default_branch="develop",
            language="Python",
            updated_at=datetime(2025, 1, 15, 10, 30),
            category="Backend",
            tags=["production", "critical"],
            branches=[BranchInfo(name="main", is_default=True)],
            codespaces=[CodespaceInfo(name="cs1", state="Available")],
            codespace_count=1,
        )
        assert r.language == "Python"
        assert r.default_branch == "develop"
        assert len(r.branches) == 1
        assert r.codespace_count == 1


class TestFlyModels:
    def test_fly_machine(self):
        m = FlyMachine(id="abc123", name="web-1", state="started", region="iad")
        assert m.id == "abc123"
        assert m.state == "started"
        assert m.image == ""

    def test_fly_app_info(self):
        app = FlyAppInfo(
            name="my-app",
            org_slug="my-org",
            status="deployed",
            hostname="my-app.fly.dev",
            machines=[FlyMachine(id="m1", name="web", state="started", region="iad")],
        )
        assert app.name == "my-app"
        assert len(app.machines) == 1
        assert app.machines[0].region == "iad"


class TestRepoView:
    def test_without_fly(self):
        repo = RepoData(org="o", name="r", full_name="o/r")
        view = RepoView(repo=repo)
        assert view.fly_app is None

    def test_with_fly(self):
        repo = RepoData(org="o", name="r", full_name="o/r")
        fly = FlyAppInfo(name="app", status="deployed")
        view = RepoView(repo=repo, fly_app=fly)
        assert view.fly_app is not None
        assert view.fly_app.name == "app"


class TestAttentionSignals:
    """Tests for the RepoView.attention computed field."""

    def _make_view(
        self,
        branches: list[BranchInfo] | None = None,
        codespace_count: int = 0,
        fly_app: FlyAppInfo | None = None,
    ) -> RepoView:
        repo = RepoData(
            org="o", name="r", full_name="o/r",
            branches=branches or [],
            codespace_count=codespace_count,
        )
        return RepoView(repo=repo, fly_app=fly_app)

    # ── all_clear ─────────────────────────────────────────────────────

    def test_all_clear_when_no_signals(self):
        view = self._make_view(branches=[BranchInfo(name="main", is_default=True)])
        assert view.attention.all_clear is True

    def test_not_clear_when_ahead(self):
        view = self._make_view(branches=[
            BranchInfo(name="main", is_default=True),
            BranchInfo(name="feat", ahead=2),
        ])
        assert view.attention.all_clear is False

    # ── branches_ahead_count ──────────────────────────────────────────

    def test_ahead_excludes_default_branch(self):
        view = self._make_view(branches=[
            BranchInfo(name="main", is_default=True, ahead=0),
            BranchInfo(name="feat-a", ahead=3),
            BranchInfo(name="feat-b", ahead=0, behind=1),
        ])
        assert view.attention.branches_ahead_count == 1

    def test_ahead_counts_multiple(self):
        view = self._make_view(branches=[
            BranchInfo(name="main", is_default=True),
            BranchInfo(name="feat-a", ahead=1),
            BranchInfo(name="feat-b", ahead=5),
            BranchInfo(name="feat-c", ahead=0),
        ])
        assert view.attention.branches_ahead_count == 2

    def test_ahead_zero_when_no_branches(self):
        view = self._make_view(branches=[])
        assert view.attention.branches_ahead_count == 0

    # ── branches_behind_count ─────────────────────────────────────────

    def test_behind_excludes_default(self):
        view = self._make_view(branches=[
            BranchInfo(name="main", is_default=True),
            BranchInfo(name="old", ahead=0, behind=4),
        ])
        assert view.attention.branches_behind_count == 1

    def test_behind_zero_when_all_current(self):
        view = self._make_view(branches=[
            BranchInfo(name="main", is_default=True),
            BranchInfo(name="feat", ahead=2, behind=0),
        ])
        assert view.attention.branches_behind_count == 0

    # ── active_codespace_count ────────────────────────────────────────

    def test_codespace_count_mirrors_repo(self):
        view = self._make_view(codespace_count=3)
        assert view.attention.active_codespace_count == 3
        assert view.attention.all_clear is False

    # ── fly_has_issues ────────────────────────────────────────────────

    def test_fly_no_app_no_issues(self):
        view = self._make_view(fly_app=None)
        assert view.attention.fly_has_issues is False

    def test_fly_suspended_app(self):
        view = self._make_view(fly_app=FlyAppInfo(name="a", status="suspended"))
        assert view.attention.fly_has_issues is True

    def test_fly_failed_machine(self):
        fly = FlyAppInfo(name="a", status="deployed", machines=[
            FlyMachine(id="m1", name="web", state="failed", region="iad"),
        ])
        view = self._make_view(fly_app=fly)
        assert view.attention.fly_has_issues is True

    def test_fly_healthy(self):
        fly = FlyAppInfo(name="a", status="deployed", machines=[
            FlyMachine(id="m1", name="web", state="started", region="iad"),
        ])
        view = self._make_view(fly_app=fly)
        assert view.attention.fly_has_issues is False

    def test_fly_status_case_insensitive(self):
        view = self._make_view(fly_app=FlyAppInfo(name="a", status="Suspended"))
        assert view.attention.fly_has_issues is True

    def test_fly_dead_app(self):
        view = self._make_view(fly_app=FlyAppInfo(name="a", status="dead"))
        assert view.attention.fly_has_issues is True

    def test_fly_stopped_machine(self):
        fly = FlyAppInfo(name="a", status="deployed", machines=[
            FlyMachine(id="m1", name="web", state="stopped", region="iad"),
        ])
        view = self._make_view(fly_app=fly)
        assert view.attention.fly_has_issues is True

    # ── combinations ──────────────────────────────────────────────────

    def test_multiple_signals(self):
        fly = FlyAppInfo(name="a", status="suspended")
        view = self._make_view(
            branches=[
                BranchInfo(name="main", is_default=True),
                BranchInfo(name="feat", ahead=1, behind=3),
            ],
            codespace_count=2,
            fly_app=fly,
        )
        sig = view.attention
        assert sig.branches_ahead_count == 1
        assert sig.branches_behind_count == 1
        assert sig.active_codespace_count == 2
        assert sig.fly_has_issues is True
        assert sig.all_clear is False

    def test_branch_both_ahead_and_behind(self):
        view = self._make_view(branches=[
            BranchInfo(name="main", is_default=True),
            BranchInfo(name="diverged", ahead=2, behind=5),
        ])
        assert view.attention.branches_ahead_count == 1
        assert view.attention.branches_behind_count == 1


class TestDashboardData:
    def test_defaults(self):
        d = DashboardData()
        assert d.repos == []
        assert d.errors == []
        assert isinstance(d.generated_at, datetime)

    def test_with_data(self):
        repo = RepoData(org="o", name="r", full_name="o/r")
        d = DashboardData(
            repos=[RepoView(repo=repo)],
            errors=["Failed to fetch org/other"],
        )
        assert len(d.repos) == 1
        assert len(d.errors) == 1
