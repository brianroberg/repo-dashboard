"""HTML dashboard route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from dashboard.auth import require_api_key
from dashboard.dependencies import get_aggregator
from dashboard.services.aggregator import Aggregator

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard_html(
    request: Request,
    _key: str = Depends(require_api_key),
    aggregator: Aggregator = Depends(get_aggregator),
) -> HTMLResponse:
    """Render the dashboard as server-side HTML."""
    data = await aggregator.build()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"data": data},
    )
