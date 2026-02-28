"""All Pydantic models: config, API responses, and view data."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, computed_field

# ── Config models ──────────────────────────────────────────────────────────────


class RepoConfig(BaseModel):
    name: str
    category: str = "Uncategorized"
    tags: list[str] = Field(default_factory=list)
    fly_app: str | None = None


class OrgConfig(BaseModel):
    name: str
    include_all: bool = True
    repos: list[RepoConfig] = Field(default_factory=list)


class FlyOrgConfig(BaseModel):
    slug: str


class DashboardConfig(BaseModel):
    github_orgs: list[OrgConfig] = Field(default_factory=list)
    fly_orgs: list[FlyOrgConfig] = Field(default_factory=list)


# ── GitHub API response models ─────────────────────────────────────────────────


class BranchInfo(BaseModel):
    name: str
    is_default: bool = False
    ahead: int = 0
    behind: int = 0


class CodespaceInfo(BaseModel):
    name: str
    state: str
    owner: str = ""


class RepoData(BaseModel):
    org: str
    name: str
    full_name: str
    description: str | None = None
    html_url: str = ""
    default_branch: str = "main"
    language: str | None = None
    updated_at: datetime | None = None
    category: str = "Uncategorized"
    tags: list[str] = Field(default_factory=list)
    branches: list[BranchInfo] = Field(default_factory=list)
    codespaces: list[CodespaceInfo] = Field(default_factory=list)
    codespace_count: int = 0


# ── Fly.io models ──────────────────────────────────────────────────────────────


class FlyMachine(BaseModel):
    id: str
    name: str
    state: str
    region: str
    image: str = ""
    created_at: str = ""
    updated_at: str = ""


class FlyAppInfo(BaseModel):
    name: str
    org_slug: str = ""
    status: str = ""
    hostname: str = ""
    machines: list[FlyMachine] = Field(default_factory=list)


# ── Attention signals ─────────────────────────────────────────────────────────

_FLY_PROBLEM_STATES: frozenset[str] = frozenset({"suspended", "failed", "stopped", "dead"})


class AttentionSignals(BaseModel):
    """Pre-computed attention indicators for a repo's collapsed card header."""

    branches_ahead_count: int = 0
    branches_behind_count: int = 0
    active_codespace_count: int = 0
    fly_has_issues: bool = False

    @property
    def all_clear(self) -> bool:
        return (
            self.branches_ahead_count == 0
            and self.branches_behind_count == 0
            and self.active_codespace_count == 0
            and not self.fly_has_issues
        )


# ── View / aggregated models ──────────────────────────────────────────────────


class RepoView(BaseModel):
    """Enriched repo data ready for display."""

    repo: RepoData
    fly_app: FlyAppInfo | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def attention(self) -> AttentionSignals:
        non_default = [b for b in self.repo.branches if not b.is_default]
        fly_has_issues = False
        if self.fly_app is not None:
            if self.fly_app.status.lower() in _FLY_PROBLEM_STATES:
                fly_has_issues = True
            elif any(m.state.lower() in _FLY_PROBLEM_STATES for m in self.fly_app.machines):
                fly_has_issues = True
        return AttentionSignals(
            branches_ahead_count=sum(1 for b in non_default if b.ahead > 0),
            branches_behind_count=sum(1 for b in non_default if b.behind > 0),
            active_codespace_count=self.repo.codespace_count,
            fly_has_issues=fly_has_issues,
        )


class DashboardData(BaseModel):
    """Top-level view model for the dashboard."""

    repos: list[RepoView] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("America/New_York"))
    )
