"""
Stub endpoints for Phases 5–9.

Each endpoint accepts a generic payload, persists a PhaseResult row,
and returns a StubResponse with phase number and ID.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.phase_result import PhaseResult
from app.schemas.stubs import StubRequest, StubResponse

router = APIRouter()

PHASE_NAMES = {
    5: "Full-text screening",
    6: "Data extraction",
    7: "Risk of bias assessment",
    9: "Publication bias assessment",
}


async def _create_phase_result(
    db: AsyncSession,
    phase_number: int,
    body: StubRequest,
) -> StubResponse:
    pr = PhaseResult(
        review_id=body.review_id,
        phase_number=phase_number,
        phase_name=PHASE_NAMES[phase_number],
        status="stub",
        result_data=body.payload,
    )
    db.add(pr)
    await db.commit()
    await db.refresh(pr)
    return StubResponse(
        phase=phase_number,
        status="stub",
        id=pr.id,
        message=f"Phase {phase_number} ({PHASE_NAMES[phase_number]}) stub recorded.",
    )


@router.post(
    "/fulltext/screen",
    response_model=StubResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["stubs"],
)
async def phase5_fulltext_screen(
    body: StubRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    """Phase 5: Full-text screening stub."""
    return await _create_phase_result(db, 5, body)


@router.post(
    "/extract",
    response_model=StubResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["stubs"],
)
async def phase6_extract(
    body: StubRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    """Phase 6: Data extraction stub."""
    return await _create_phase_result(db, 6, body)


@router.post(
    "/rob/assess",
    response_model=StubResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["stubs"],
)
async def phase7_rob_assess(
    body: StubRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    """Phase 7: Risk of bias assessment stub."""
    return await _create_phase_result(db, 7, body)


@router.post(
    "/pubias/assess",
    response_model=StubResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["stubs"],
)
async def phase9_pubias_assess(
    body: StubRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    """Phase 9: Publication bias assessment stub."""
    return await _create_phase_result(db, 9, body)
