"""JSON API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from dashboard.auth import require_api_key
from dashboard.dependencies import get_aggregator
from dashboard.models import DashboardData
from dashboard.services.aggregator import Aggregator

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/dashboard", response_model=DashboardData)
async def dashboard_json(
    _key: str = Depends(require_api_key),
    aggregator: Aggregator = Depends(get_aggregator),
) -> DashboardData:
    """Return full dashboard data as JSON."""
    return await aggregator.build()
