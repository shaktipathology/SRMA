from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.sof import SofRequest, SofResponse
from app.services.sof_generator import generate_sof_b64

router = APIRouter()


@router.post("", response_model=SofResponse, status_code=status.HTTP_201_CREATED)
async def create_sof_table(
    body: SofRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SofResponse:
    """
    Phase 11a: Generate a Summary of Findings (SoF) table as a DOCX file.

    Returns the DOCX as a base64-encoded string.
    """
    try:
        docx_b64 = generate_sof_b64(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"SoF table generation failed: {exc}",
        ) from exc

    return SofResponse(docx_b64=docx_b64, outcomes_count=len(body.outcomes))
