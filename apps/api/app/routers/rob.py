"""
POST /api/v1/rob/assess  —  Phase 7: Risk of bias assessment.

Workflow:
1. Resolve papers:
   - explicit paper_ids, OR
   - all papers for the review with screening_label = 'include'
2. For each paper build full text (grobid_tei stripped → else abstract)
3. Call Claude with the appropriate RoB tool (RoB 2 or ROBINS-I)
4. Persist a RobAssessment row per paper
5. Return batch summary with counts per overall judgment
"""
from __future__ import annotations

import asyncio
import re
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.paper import Paper
from app.models.rob_assessment import RobAssessment
from app.schemas.rob import RobAssessRequest, RobAssessmentOut, RobBatchResponse
from app.services import claude as claude_svc

router = APIRouter()

MODEL = "claude-sonnet-4-6"


def _paper_text(paper: Paper) -> str:
    if paper.grobid_tei:
        plain = re.sub(r"<[^>]+>", " ", paper.grobid_tei)
        return re.sub(r"\s{2,}", " ", plain).strip()
    return paper.abstract or ""


@router.post(
    "/assess",
    response_model=RobBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assess_rob(
    body: RobAssessRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RobBatchResponse:
    """
    Phase 7: Risk of bias assessment using Cochrane RoB 2 (RCTs) or
    ROBINS-I (observational studies) via Claude.

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
            detail="Provide either review_id or explicit paper_ids.",
        )

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No included papers found for risk of bias assessment.",
        )

    # ── 2. Assess each paper ─────────────────────────────────────────────
    async def _assess_one(paper: Paper):
        text = _paper_text(paper)
        try:
            result = await claude_svc.assess_rob(
                title=paper.title,
                full_text=text,
                tool=body.tool,
            )
            return (
                paper.id,
                result.get("domains", []),
                result.get("overall_judgment", "some_concerns"),
                "complete",
            )
        except Exception as exc:
            return paper.id, [], None, "error"

    results = await asyncio.gather(*[_assess_one(p) for p in papers])

    # ── 3. Persist RobAssessment rows ────────────────────────────────────
    assessments: List[RobAssessment] = []
    for paper_id, domains, overall, rob_status in results:
        ra = RobAssessment(
            review_id=body.review_id,
            paper_id=paper_id,
            tool=body.tool,
            domain_judgments=domains,
            overall_judgment=overall,
            assessor_model=MODEL,
            status=rob_status,
        )
        db.add(ra)
        assessments.append(ra)

    await db.commit()
    for ra in assessments:
        await db.refresh(ra)

    # ── 4. Build response ─────────────────────────────────────────────────
    successful = sum(1 for a in assessments if a.status == "complete")
    return RobBatchResponse(
        assessed=len(papers),
        successful=successful,
        failed=len(papers) - successful,
        low_risk=sum(1 for a in assessments if a.overall_judgment == "low"),
        some_concerns=sum(1 for a in assessments if a.overall_judgment == "some_concerns"),
        high_risk=sum(1 for a in assessments if a.overall_judgment == "high"),
        assessments=[RobAssessmentOut.model_validate(a) for a in assessments],
    )
