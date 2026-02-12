"""Orchestrates GitHub + Fly clients into DashboardData."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from dashboard.clients.fly import FlyClient
from dashboard.clients.github import GitHubClient
from dashboard.models import (
    BranchInfo,
    CodespaceInfo,
    DashboardConfig,
    DashboardData,
    FlyAppInfo,
    FlyMachine,
    OrgConfig,
    RepoData,
    RepoView,
)

logger = logging.getLogger(__name__)


class Aggregator:
    def __init__(
        self,
        config: DashboardConfig,
        github: GitHubClient,
        fly: FlyClient | None = None,
    ) -> None:
        self._config = config
        self._github = github
        self._fly = fly

    async def build(self) -> DashboardData:
        """Build complete dashboard data from all configured sources."""
        errors: list[str] = []
        repo_views: list[RepoView] = []

        # Build fly app lookup: app_name → FlyAppInfo
        fly_lookup: dict[str, FlyAppInfo] = {}
        if self._fly:
            fly_lookup = await self._build_fly_lookup(errors)

        # Fetch repos per org
        for org_config in self._config.github_orgs:
            org_repos = await self._fetch_org_repos(org_config, errors)
            for repo_view in org_repos:
                # Attach Fly app if mapped
                fly_app_name = self._get_fly_app_name(org_config, repo_view.repo.name)
                if fly_app_name and fly_app_name in fly_lookup:
                    repo_view.fly_app = fly_lookup[fly_app_name]
                repo_views.append(repo_view)

        return DashboardData(repos=repo_views, errors=errors)

    async def _build_fly_lookup(self, errors: list[str]) -> dict[str, FlyAppInfo]:
        """Fetch all Fly apps and index by name."""
        assert self._fly is not None
        lookup: dict[str, FlyAppInfo] = {}

        for fly_org in self._config.fly_orgs:
            try:
                apps = await self._fly.list_apps(fly_org.slug)
                for app_data in apps:
                    app_name = app_data.get("name", "")
                    if not app_name:
                        continue
                    try:
                        machines_data = await self._fly.list_machines(app_name)
                        machines = [
                            FlyMachine(
                                id=m.get("id", ""),
                                name=m.get("name", ""),
                                state=m.get("state", "unknown"),
                                region=m.get("region", ""),
                                image=m.get("image", ""),
                            )
                            for m in machines_data
                        ]
                    except Exception as exc:
                        errors.append(f"Fly machines for {app_name}: {exc}")
                        machines = []

                    lookup[app_name] = FlyAppInfo(
                        name=app_name,
                        org_slug=fly_org.slug,
                        status=app_data.get("status", ""),
                        hostname=app_data.get("hostname", ""),
                        machines=machines,
                    )
            except Exception as exc:
                errors.append(f"Fly org {fly_org.slug}: {exc}")

        return lookup

    async def _fetch_org_repos(self, org_config: OrgConfig, errors: list[str]) -> list[RepoView]:
        """Fetch and enrich repos for a single org."""
        repo_overrides = {r.name: r for r in org_config.repos}
        repos_to_process: list[dict[str, Any]] = []

        if org_config.include_all:
            try:
                all_repos = await self._github.list_org_repos(org_config.name)
                repos_to_process = all_repos
            except Exception as exc:
                errors.append(f"GitHub org {org_config.name}: {exc}")
                return []
        else:
            # Only fetch explicitly listed repos — use org repo list filtered
            try:
                all_repos = await self._github.list_org_repos(org_config.name)
                listed_names = {r.name for r in org_config.repos}
                repos_to_process = [r for r in all_repos if r.get("name") in listed_names]
            except Exception as exc:
                errors.append(f"GitHub org {org_config.name}: {exc}")
                return []

        # Enrich each repo concurrently
        tasks = [
            self._enrich_repo(org_config.name, repo_data, repo_overrides, errors)
            for repo_data in repos_to_process
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        views: list[RepoView] = []
        for result in results:
            if isinstance(result, Exception):
                errors.append(f"Enriching repo: {result}")
            else:
                views.append(result)

        return views

    async def _enrich_repo(
        self,
        org: str,
        repo_data: dict[str, Any],
        overrides: dict[str, Any],
        errors: list[str],
    ) -> RepoView:
        """Enrich a single repo with branches, codespaces, and config overrides."""
        repo_name = repo_data["name"]
        default_branch = repo_data.get("default_branch", "main")

        # Apply config overrides
        override = overrides.get(repo_name)
        category = override.category if override else "Uncategorized"
        tags = override.tags if override else []

        # Fetch branches and codespaces concurrently
        branch_task = self._fetch_branches(org, repo_name, default_branch, errors)
        codespace_task = self._fetch_codespaces(org, repo_name, errors)
        branches, codespaces = await asyncio.gather(branch_task, codespace_task)

        repo = RepoData(
            org=org,
            name=repo_name,
            full_name=repo_data.get("full_name", f"{org}/{repo_name}"),
            description=repo_data.get("description"),
            html_url=repo_data.get("html_url", ""),
            default_branch=default_branch,
            language=repo_data.get("language"),
            updated_at=repo_data.get("updated_at"),
            category=category,
            tags=tags,
            branches=branches,
            codespaces=codespaces,
            codespace_count=len(codespaces),
        )

        return RepoView(repo=repo)

    async def _fetch_branches(
        self, org: str, repo: str, default_branch: str, errors: list[str]
    ) -> list[BranchInfo]:
        """Fetch branches and compare each non-default branch to default."""
        try:
            raw_branches = await self._github.list_branches(org, repo)
        except Exception as exc:
            errors.append(f"Branches for {org}/{repo}: {exc}")
            return []

        branches: list[BranchInfo] = []
        for b in raw_branches:
            name = b["name"]
            is_default = name == default_branch
            ahead = 0
            behind = 0

            if not is_default:
                try:
                    comparison = await self._github.compare_branches(
                        org, repo, default_branch, name
                    )
                    ahead = comparison.get("ahead_by", 0)
                    behind = comparison.get("behind_by", 0)
                except Exception:
                    pass  # Non-critical — just skip comparison data

            branches.append(
                BranchInfo(
                    name=name,
                    is_default=is_default,
                    ahead=ahead,
                    behind=behind,
                )
            )

        return branches

    async def _fetch_codespaces(
        self, org: str, repo: str, errors: list[str]
    ) -> list[CodespaceInfo]:
        """Fetch codespaces for a repo."""
        try:
            raw = await self._github.list_codespaces(org, repo)
            return [
                CodespaceInfo(
                    name=cs.get("name", ""),
                    state=cs.get("state", "Unknown"),
                    owner=cs.get("owner", {}).get("login", ""),
                )
                for cs in raw
            ]
        except Exception as exc:
            errors.append(f"Codespaces for {org}/{repo}: {exc}")
            return []

    def _get_fly_app_name(self, org_config: OrgConfig, repo_name: str) -> str | None:
        """Look up explicit Fly app mapping from config."""
        for repo_cfg in org_config.repos:
            if repo_cfg.name == repo_name:
                return repo_cfg.fly_app
        return None
