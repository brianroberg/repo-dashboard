"""API key authentication dependency."""

from __future__ import annotations

import os

from fastapi import HTTPException, Query, Request


def require_api_key(
    request: Request,
    api_key: str | None = Query(None, alias="api_key"),
) -> str:
    """FastAPI dependency that validates an API key.

    Accepts the key via:
    - Query parameter: ?api_key=<key>
    - Header: X-API-Key: <key>
    """
    expected = os.environ.get("DASHBOARD_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="DASHBOARD_API_KEY not configured")

    provided = api_key or request.headers.get("X-API-Key")
    if not provided:
        raise HTTPException(status_code=401, detail="API key required")

    if provided != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return provided
