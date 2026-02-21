from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.manuscript import ManuscriptRequest, ManuscriptResponse
from app.services.manuscript_builder import build_manuscript

router = APIRouter()


@router.post("", response_model=ManuscriptResponse, status_code=status.HTTP_201_CREATED)
async def create_manuscript(
    body: ManuscriptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ManuscriptResponse:
    """
    Phase 11b: Assemble a full manuscript DOCX from all available phase data.

    Reads DB for the review, generates each section from data or placeholders,
    optionally calling Claude for narrative sections.
    Returns the DOCX as a base64-encoded string.
    """
    try:
        result = await build_manuscript(db=db, request=body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Manuscript assembly failed: {exc}",
        ) from exc

    return result
