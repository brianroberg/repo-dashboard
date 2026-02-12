"""All Pydantic models: config, API responses, and view data."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

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


# ── View / aggregated models ──────────────────────────────────────────────────


class RepoView(BaseModel):
    """Enriched repo data ready for display."""

    repo: RepoData
    fly_app: FlyAppInfo | None = None


class DashboardData(BaseModel):
    """Top-level view model for the dashboard."""

    repos: list[RepoView] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
