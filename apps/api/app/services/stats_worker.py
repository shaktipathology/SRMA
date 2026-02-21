"""
Async HTTP client for the Stats Worker microservice (port 8001).

Follows the same pattern as ncbi.py — thin async wrapper, no business logic.
"""
from __future__ import annotations

from typing import Any, Dict

import httpx

from app.core.config import settings


async def run_pool(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /pool to the stats worker.

    payload keys: study_labels, effect_sizes, standard_errors, measure, method
    Returns the full PoolResponse dict including forest_plot (base64 PNG).
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.stats_worker_url}/pool",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
