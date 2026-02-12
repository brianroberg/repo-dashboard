"""Tests for config loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dashboard.config import load_config
from dashboard.models import DashboardConfig


@pytest.fixture
def tmp_config(tmp_path):
    """Helper to write a temporary config file and return its path."""

    def _write(content: str) -> Path:
        p = tmp_path / "config.yaml"
        p.write_text(content)
        return p

    return _write


class TestLoadConfig:
    def test_load_minimal(self, tmp_config):
        path = tmp_config("github_orgs: []")
        config = load_config(path)
        assert isinstance(config, DashboardConfig)
        assert config.github_orgs == []
        assert config.fly_orgs == []

    def test_load_full(self, tmp_config):
        path = tmp_config("""
github_orgs:
  - name: "my-org"
    include_all: true
    repos:
      - name: "web-app"
        category: "Frontend"
        tags: ["production"]
        fly_app: "web-app-prod"
  - name: "other-org"
    include_all: false
    repos:
      - name: "shared-lib"
        category: "Libraries"
fly_orgs:
  - slug: "my-fly-org"
""")
        config = load_config(path)
        assert len(config.github_orgs) == 2
        assert config.github_orgs[0].name == "my-org"
        assert config.github_orgs[0].include_all is True
        assert config.github_orgs[0].repos[0].name == "web-app"
        assert config.github_orgs[0].repos[0].category == "Frontend"
        assert config.github_orgs[0].repos[0].tags == ["production"]
        assert config.github_orgs[0].repos[0].fly_app == "web-app-prod"
        assert config.github_orgs[1].include_all is False
        assert len(config.fly_orgs) == 1
        assert config.fly_orgs[0].slug == "my-fly-org"

    def test_defaults(self, tmp_config):
        path = tmp_config("""
github_orgs:
  - name: "org1"
    repos:
      - name: "repo1"
""")
        config = load_config(path)
        org = config.github_orgs[0]
        assert org.include_all is True
        repo = org.repos[0]
        assert repo.category == "Uncategorized"
        assert repo.tags == []
        assert repo.fly_app is None

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_invalid_yaml(self, tmp_config):
        path = tmp_config("- this\nis: not: valid: yaml: [")
        with pytest.raises((ValueError, yaml.YAMLError)):
            load_config(path)

    def test_non_mapping_yaml(self, tmp_config):
        path = tmp_config("- just\n- a\n- list")
        with pytest.raises(ValueError, match="YAML mapping"):
            load_config(path)

    def test_empty_yaml(self, tmp_config):
        path = tmp_config("")
        config = load_config(path)
        assert isinstance(config, DashboardConfig)
        assert config.github_orgs == []

    def test_env_var_path(self, tmp_config, monkeypatch):
        path = tmp_config("github_orgs:\n  - name: env-org")
        monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(path))
        config = load_config()
        assert config.github_orgs[0].name == "env-org"
