from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


async def get_pubmed_count(search_string: str) -> int:
    """Run a PubMed esearch and return the estimated record count."""
    params = {
        "db": "pubmed",
        "term": search_string,
        "retmode": "json",
        "retmax": "0",
    }
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ESEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

    count_str = data.get("esearchresult", {}).get("count", "0")
    return int(count_str)
