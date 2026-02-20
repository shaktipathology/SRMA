from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.search_query import SearchQuery
from app.schemas.search import SearchBuildRequest, SearchBuildResponse
from app.services import claude as claude_svc
from app.services import ncbi

router = APIRouter()

MODEL = "claude-sonnet-4-6"


@router.post("/build", response_model=SearchBuildResponse, status_code=status.HTTP_201_CREATED)
async def build_search(
    body: SearchBuildRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchBuildResponse:
    """
    Phase 2: Build a PubMed search string from a PICO schema using Claude,
    then query NCBI Entrez for the estimated record count.
    """
    # Call Claude to build the search string
    try:
        claude_result = await claude_svc.build_pubmed_search(body.pico_schema)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
        ) from exc

    search_string: str = claude_result.get("search_string", "")
    rationale: str = claude_result.get("rationale", "")

    # Query NCBI for estimated yield
    estimated_yield: int | None = None
    if search_string:
        try:
            estimated_yield = await ncbi.get_pubmed_count(search_string)
        except Exception:
            estimated_yield = None

    # Persist to DB
    sq = SearchQuery(
        review_id=body.review_id,
        protocol_version_id=body.protocol_version_id,
        pico_schema=body.pico_schema,
        search_string=search_string,
        estimated_yield=estimated_yield,
        database="pubmed",
        claude_model=MODEL,
    )
    db.add(sq)
    await db.commit()
    await db.refresh(sq)

    resp = SearchBuildResponse.model_validate(sq)
    resp.rationale = rationale
    return resp
