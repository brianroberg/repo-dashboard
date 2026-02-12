"""YAML config loading → DashboardConfig."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from dashboard.models import DashboardConfig


def load_config(path: str | Path | None = None) -> DashboardConfig:
    """Load dashboard config from YAML file.

    Resolution order for path:
    1. Explicit `path` argument
    2. DASHBOARD_CONFIG_PATH env var
    3. Default: config.yaml in current directory
    """
    if path is None:
        path = os.environ.get("DASHBOARD_CONFIG_PATH", "config.yaml")

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    text = config_path.read_text()
    data = yaml.safe_load(text)

    if data is None:
        return DashboardConfig()

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping, got {type(data).__name__}")

    return DashboardConfig(**data)
