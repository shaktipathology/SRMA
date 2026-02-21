"""
POST /api/v1/extract  —  Phase 6: Structured data extraction from included papers.

Workflow:
1. Resolve papers:
   - explicit paper_ids, OR
   - all papers for the review with screening_label = 'include'
2. For each paper build full text (grobid_tei → stripped, else abstract)
3. Call Claude to extract structured fields (study design, population, n,
   outcomes with effect sizes, etc.)
4. Persist a DataExtraction row per paper
5. Return batch summary
"""
from __future__ import annotations

import asyncio
import re
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.data_extraction import DataExtraction
from app.models.paper import Paper
from app.schemas.extract import ExtractBatchResponse, ExtractRequest, ExtractionOut
from app.services import claude as claude_svc

router = APIRouter()

MODEL = "claude-sonnet-4-6"


def _paper_text(paper: Paper) -> str:
    """Return the best available text for a paper."""
    if paper.grobid_tei:
        plain = re.sub(r"<[^>]+>", " ", paper.grobid_tei)
        return re.sub(r"\s{2,}", " ", plain).strip()
    return paper.abstract or ""


@router.post(
    "",
    response_model=ExtractBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def extract_data(
    body: ExtractRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExtractBatchResponse:
    """
    Phase 6: Extract structured data from included papers using Claude.

    If paper_ids is omitted, automatically targets all papers with
    screening_label='include' for the given review_id.
    """
    # ── 1. Resolve papers ────────────────────────────────────────────────
    if body.paper_ids:
        result = await db.execute(
            select(Paper).where(Paper.id.in_(body.paper_ids))
        )
        papers: List[Paper] = list(result.scalars().all())
    elif body.review_id:
        result = await db.execute(
            select(Paper).where(
                Paper.review_id == body.review_id,
                Paper.screening_label == "include",
            )
        )
        papers = list(result.scalars().all())
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either review_id (to auto-select included papers) or explicit paper_ids.",
        )

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No included papers found for data extraction.",
        )

    # ── 2. Extract data from each paper ──────────────────────────────────
    async def _extract_one(paper: Paper):
        text = _paper_text(paper)
        try:
            data = await claude_svc.extract_paper_data(
                title=paper.title,
                full_text=text,
                extraction_template=body.extraction_template,
            )
            return paper.id, data, "complete"
        except Exception as exc:
            return paper.id, {"error": str(exc)}, "error"

    results = await asyncio.gather(*[_extract_one(p) for p in papers])

    # ── 3. Persist DataExtraction rows ───────────────────────────────────
    extractions: List[DataExtraction] = []
    for paper_id, data, extraction_status in results:
        de = DataExtraction(
            review_id=body.review_id,
            paper_id=paper_id,
            extracted_data=data,
            extractor_model=MODEL,
            status=extraction_status,
        )
        db.add(de)
        extractions.append(de)

    await db.commit()
    for de in extractions:
        await db.refresh(de)

    # ── 4. Build response ─────────────────────────────────────────────────
    successful = sum(1 for de in extractions if de.status == "complete")
    return ExtractBatchResponse(
        extracted=len(papers),
        successful=successful,
        failed=len(papers) - successful,
        extractions=[ExtractionOut.model_validate(de) for de in extractions],
    )
