"""HTML dashboard route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from dashboard.dependencies import get_aggregator
from dashboard.services.aggregator import Aggregator

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    aggregator: Aggregator = Depends(get_aggregator),
) -> HTMLResponse:
    """Serve the full dashboard page with live data."""
    data = await aggregator.build()
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "dashboard.html", {"data": data})
