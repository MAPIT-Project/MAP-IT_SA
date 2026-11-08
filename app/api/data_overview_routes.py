"""Authenticated public-source aggregates; no private user or document content."""

import time
from fastapi import APIRouter, Depends, Response
from app.core.auth import get_current_user
from app.services.data_overview import data_overview

router = APIRouter(prefix="/api/data-overview", tags=["data-overview"])
_cache = None
_cache_until = 0.0


@router.get("")
async def overview(response: Response, refresh: bool = False, user=Depends(get_current_user)):
    global _cache, _cache_until
    if refresh or _cache is None or time.monotonic() >= _cache_until:
        result = await data_overview()
        _cache = result
        _cache_until = time.monotonic() + (30 if result["status"] == "available" else 5)
    response.headers["Cache-Control"] = "private, no-store"
    return _cache
