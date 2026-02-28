"""Authenticated HTML content fragment route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from dashboard.auth import require_api_key
from dashboard.dependencies import get_aggregator
from dashboard.services.aggregator import Aggregator

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/dashboard/html", response_class=HTMLResponse)
async def dashboard_html_fragment(
    request: Request,
    _key: str = Depends(require_api_key),
    aggregator: Aggregator = Depends(get_aggregator),
) -> HTMLResponse:
    """Return dashboard content as an HTML fragment.

    Called by the client-side auth layer after the API key is validated.
    Auth failures propagate as JSON HTTPException (401/403).
    """
    data = await aggregator.build()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "partials/dashboard_content.html",
        {"data": data},
    )
