"""HTML dashboard route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> HTMLResponse:
    """Serve the dashboard shell page.

    No authentication required — the page always loads.
    The client-side auth layer (auth.js) handles API key
    collection and fetches dashboard content after validation.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "dashboard.html", {})
