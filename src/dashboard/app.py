"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dashboard.config import load_config
from dashboard.routes import api, content, dashboard

PACKAGE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage shared resources across the app lifetime."""
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


def create_app(config_path: str | Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    config = load_config(config_path)

    app = FastAPI(title="Repo Dashboard", lifespan=lifespan)
    app.state.config = config

    # Templates
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    app.state.templates = templates

    # Static files
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    # Routes
    app.include_router(dashboard.router)
    app.include_router(api.router)
    app.include_router(content.router)

    return app
