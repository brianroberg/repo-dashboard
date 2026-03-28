# Repo Dashboard

A single-page dashboard that shows all your GitHub projects across multiple orgs at a glance. Fetches live data from the GitHub REST API and Fly.io Machines API on each page load. No database, no caching, no background jobs — just a clean, real-time view of your repositories.

![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.115+-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

- **Multi-org support** — aggregate repos from multiple GitHub organizations in one view
- **Branch tracking** — see all branches with ahead/behind counts relative to the default branch
- **Codespace visibility** — track active GitHub Codespaces per repo
- **Fly.io deployments** — view machine status, regions, and hostnames for mapped Fly apps
- **Partial failure tolerance** — if one API call fails, the rest of the dashboard still renders
- **Dual access** — server-rendered HTML dashboard and a JSON API endpoint
- **YAML config** — declarative org/repo configuration with per-repo overrides
- **Dark theme** — GitHub-inspired dark UI designed for information density
- **Keyboard shortcuts** — press `e` to expand all cards, `c` to collapse all
- **Docker deployment** — ready-to-deploy with Docker Compose behind a reverse proxy

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A [GitHub Personal Access Token](https://github.com/settings/tokens) with `repo` and `codespace` scopes

### Installation

```bash
git clone <repo-url> && cd repo-dashboard
uv sync --all-extras
```

### Configuration

1. **Create your config file:**

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to list your orgs and repos:

```yaml
github_orgs:
  - name: "my-org"
    include_all: true            # fetch every repo in the org
    repos:
      - name: "web-app"
        category: "Frontend"
        tags: ["production"]
        fly_app: "web-app-prod"  # link to a Fly.io app

  - name: "other-org"
    include_all: false           # only fetch repos listed below
    repos:
      - name: "shared-lib"
        category: "Libraries"

fly_orgs:
  - slug: "my-fly-org"
```

2. **Set environment variables:**

```bash
cp .env.example .env
```

Edit `.env` with your tokens:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx       # required
FLY_API_TOKEN=fly_xxxxxxxxxx         # optional
```

### Run

```bash
uv run uvicorn dashboard.app:create_app --factory --reload --env-file .env
```

Then open `http://localhost:8000/`.

> **Note:** This dashboard has no built-in authentication. When deploying, restrict access at the network or reverse proxy layer (e.g., Caddy with basic auth, Tailscale, VPN).

## Docker Deployment

Build and run with Docker Compose:

```bash
docker compose up -d
```

Prerequisites:
- A `.env` file with at least `GITHUB_TOKEN` set
- A `config.yaml` in the project root (bind-mounted into the container)
- The external Docker network `caddy_net` must exist: `docker network create caddy_net`

The compose file expects a Caddy (or similar) reverse proxy on the `caddy_net` network to handle external access.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Yes | GitHub PAT with `repo` + `codespace` scopes |
| `FLY_API_TOKEN` | No | Fly.io API token; deployment info is skipped if not set |
| `DASHBOARD_CONFIG_PATH` | No | Path to YAML config file (default: `config.yaml`) |

## Config Reference

### `github_orgs[]`

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | *required* | GitHub organization name |
| `include_all` | bool | `true` | Fetch all repos in the org |
| `repos` | list | `[]` | Per-repo configuration overrides |

### `github_orgs[].repos[]`

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | *required* | Repository name |
| `category` | string | `"Uncategorized"` | Display grouping label |
| `tags` | list[string] | `[]` | Custom tags shown as badges |
| `fly_app` | string | `null` | Name of the linked Fly.io app |

### `fly_orgs[]`

| Field | Type | Default | Description |
|---|---|---|---|
| `slug` | string | *required* | Fly.io organization slug |

## API Endpoints

### `GET /`

Serves the full dashboard page with live data, rendered server-side.

### `GET /api/dashboard`

Returns the full dashboard data as JSON.

```bash
curl http://localhost:8000/api/dashboard | python -m json.tool
```

Response shape:

```json
{
  "repos": [
    {
      "repo": {
        "org": "my-org",
        "name": "web-app",
        "full_name": "my-org/web-app",
        "description": "...",
        "html_url": "https://github.com/my-org/web-app",
        "default_branch": "main",
        "language": "Python",
        "updated_at": "2025-01-15T10:30:00Z",
        "category": "Frontend",
        "tags": ["production"],
        "branches": [
          { "name": "main", "is_default": true, "ahead": 0, "behind": 0 },
          { "name": "feature-x", "is_default": false, "ahead": 3, "behind": 1 }
        ],
        "codespaces": [
          { "name": "refactor-auth", "state": "Available", "owner": "alice" }
        ],
        "codespace_count": 1
      },
      "fly_app": {
        "name": "web-app-prod",
        "status": "deployed",
        "hostname": "web-app-prod.fly.dev",
        "machines": [
          { "id": "abc123", "name": "web", "state": "started", "region": "iad" }
        ]
      }
    }
  ],
  "errors": [],
  "generated_at": "2025-01-15T12:00:00Z"
}
```

## Architecture

```
GET /              → Aggregator → ┬─ GitHubClient
                                  └─ FlyClient
                                       ↓
                                  DashboardData → Jinja2 → full HTML page
GET /api/dashboard → Aggregator → JSON
```

Key design decisions:

- **App factory pattern** — `create_app()` returns a configured FastAPI instance; lifespan manages a shared `httpx.AsyncClient` for connection pooling
- **Aggregator as sole orchestrator** — routes never call API clients directly; all data flows through the aggregator
- **Concurrent enrichment** — branches and codespaces for each repo are fetched in parallel via `asyncio.gather`
- **Partial failure** — `asyncio.gather(return_exceptions=True)` collects errors into a list; the dashboard renders whatever data is available
- **Server-side rendering** — Jinja2 does all HTML rendering; JavaScript handles expand/collapse and client-side sorting/filtering

## Project Structure

```
src/dashboard/
├── app.py              # FastAPI factory, lifespan, router registration
├── config.py           # YAML loading → DashboardConfig
├── models.py           # All Pydantic models (config, API, view)
├── dependencies.py     # get_aggregator dependency
├── clients/
│   ├── github.py       # GitHub REST API client
│   └── fly.py          # Fly.io Machines API client
├── services/
│   └── aggregator.py   # Orchestrates clients → DashboardData
├── routes/
│   ├── dashboard.py    # GET / → full server-rendered dashboard
│   └── api.py          # GET /api/dashboard → JSON
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   └── partials/
│       ├── dashboard_content.html  # Dashboard body (filter toolbar, repo grid)
│       └── repo_card.html
└── static/
    ├── style.css
    └── dashboard.js    # Card toggle, filters, sorting, keyboard shortcuts
```

## Development

### Install dependencies

```bash
uv sync --all-extras
```

### Run tests

```bash
uv run pytest -v
```

The test suite covers config loading, all Pydantic models, both API clients, the aggregator service, and both route handlers. API client tests use `httpx.MockTransport` — no real HTTP calls are made.

### Lint and format

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Run the dev server

```bash
uv run uvicorn dashboard.app:create_app --factory --reload --env-file .env
```

## License

MIT
