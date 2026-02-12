"""FastAPI dependencies for injecting services."""

from __future__ import annotations

import os

from fastapi import Request

from dashboard.clients.fly import FlyClient
from dashboard.clients.github import GitHubClient
from dashboard.models import DashboardConfig
from dashboard.services.aggregator import Aggregator


def get_aggregator(request: Request) -> Aggregator:
    """Build an Aggregator from app state. Used as a FastAPI dependency."""
    config: DashboardConfig = request.app.state.config
    http = request.app.state.http_client

    github_token = os.environ.get("GITHUB_TOKEN", "")
    github = GitHubClient(http, github_token)

    fly_token = os.environ.get("FLY_API_TOKEN")
    fly = FlyClient(http, fly_token) if fly_token else None

    return Aggregator(config, github, fly)
