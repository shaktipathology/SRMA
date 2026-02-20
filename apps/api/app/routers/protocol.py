from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.protocol_version import ProtocolVersion
from app.schemas.protocol import ProtocolRequest, ProtocolResponse
from app.services import claude as claude_svc
from app.services import minio_store

router = APIRouter()

MODEL = "claude-sonnet-4-6"


@router.post("", response_model=ProtocolResponse, status_code=status.HTTP_201_CREATED)
async def create_protocol(
    body: ProtocolRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProtocolResponse:
    """
    Phase 1: Extract PICO from a research question using Claude
    and persist the result in MinIO + DB.
    """
    # Determine next version number for this review
    version = 1
    if body.review_id is not None:
        result = await db.execute(
            select(func.max(ProtocolVersion.version)).where(
                ProtocolVersion.review_id == body.review_id
            )
        )
        max_ver = result.scalar_one_or_none()
        if max_ver is not None:
            version = max_ver + 1

    # Call Claude to extract PICO
    try:
        pico_schema = await claude_svc.extract_pico(body.research_question)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
        ) from exc

    # Write to MinIO
    minio_prefix: str | None = None
    if body.review_id is not None:
        try:
            minio_prefix = await minio_store.put_protocol_files(
                review_id=str(body.review_id),
                version=version,
                pico_schema=pico_schema,
                research_question=body.research_question,
            )
        except Exception as exc:
            # MinIO failure is non-fatal — log and continue
            minio_prefix = None

    # Persist to DB
    pv = ProtocolVersion(
        review_id=body.review_id,
        version=version,
        research_question=body.research_question,
        pico_schema=pico_schema,
        minio_prefix=minio_prefix,
        claude_model=MODEL,
    )
    db.add(pv)
    await db.commit()
    await db.refresh(pv)

    return ProtocolResponse.model_validate(pv)
