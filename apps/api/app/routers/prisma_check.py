from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.prisma_check import PrismaCheckRequest, PrismaCheckResponse
from app.services.prisma_validator import validate_prisma

router = APIRouter()


@router.post("/validate", response_model=PrismaCheckResponse, status_code=status.HTTP_200_OK)
async def check_prisma(
    body: PrismaCheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PrismaCheckResponse:
    """
    Phase 11c: Validate the review against the PRISMA 2020 27-item checklist.

    Checks DB state for the review and returns per-item compliance status.
    """
    try:
        result = await validate_prisma(db=db, review_id=body.review_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PRISMA validation failed: {exc}",
        ) from exc

    return result
