"""
POST /api/v1/screen/batch

Workflow:
1. Fetch requested papers from DB
2. Jaro-Winkler deduplication on titles
3. Dual-agent parallel Claude screening for non-duplicates
4. Compute Cohen's κ across the batch
5. Persist ScreeningDecision rows + update Paper.screening_label
6. Return batch summary
"""
from __future__ import annotations

import asyncio
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.paper import Paper
from app.models.screening_decision import ScreeningDecision
from app.schemas.screening import ScreenBatchRequest, ScreenBatchResponse, ScreeningDecisionOut
from app.services import dedup as dedup_svc
from app.services import screener as screener_svc
from app.services import kappa as kappa_svc

router = APIRouter()

MODEL = "claude-sonnet-4-6"


@router.post("/batch", response_model=ScreenBatchResponse, status_code=status.HTTP_201_CREATED)
async def screen_batch(
    body: ScreenBatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScreenBatchResponse:
    if not body.paper_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="paper_ids must be non-empty")

    # ── 1. Fetch papers ───────────────────────────────────────────────────
    result = await db.execute(
        select(Paper).where(Paper.id.in_(body.paper_ids))
    )
    papers: List[Paper] = list(result.scalars().all())

    if not papers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No papers found for the given IDs")

    # ── 2. Jaro-Winkler deduplication ────────────────────────────────────
    id_title_pairs = [(p.id, p.title) for p in papers]
    dup_map = dedup_svc.find_duplicates(id_title_pairs)  # paper_id → None | dup_of_id

    paper_by_id = {p.id: p for p in papers}

    # ── 3. Parallel dual-agent screening for non-duplicates ──────────────
    non_dup_papers = [p for p in papers if dup_map[p.id] is None]

    async def _screen_one(paper: Paper):
        try:
            a1, a2 = await screener_svc.screen_paper(
                title=paper.title,
                abstract=paper.abstract,
                criteria=body.inclusion_criteria,
            )
        except Exception as exc:
            # Graceful degradation: mark uncertain on error
            a1 = {"label": "uncertain", "reasoning": f"Agent error: {exc}"}
            a2 = {"label": "uncertain", "reasoning": f"Agent error: {exc}"}
        return paper.id, a1, a2

    screen_results = await asyncio.gather(*[_screen_one(p) for p in non_dup_papers])

    # ── 4. Cohen's κ ─────────────────────────────────────────────────────
    a1_labels = [r[1]["label"] for r in screen_results]
    a2_labels = [r[2]["label"] for r in screen_results]
    kappa = kappa_svc.compute_kappa(a1_labels, a2_labels)

    # ── 5. Persist decisions ──────────────────────────────────────────────
    decisions: List[ScreeningDecision] = []

    # Duplicate papers — create decisions with is_duplicate=True, no agent labels
    for paper in papers:
        dup_of = dup_map[paper.id]
        if dup_of is not None:
            sd = ScreeningDecision(
                paper_id=paper.id,
                review_id=body.review_id,
                is_duplicate=True,
                duplicate_of_paper_id=dup_of,
                final_label="exclude",
                claude_model=MODEL,
            )
            db.add(sd)
            decisions.append(sd)
            # Update paper label
            paper.screening_label = "exclude"

    # Screened papers
    for paper_id, a1, a2 in screen_results:
        final = screener_svc.resolve_final_label(a1["label"], a2["label"])
        sd = ScreeningDecision(
            paper_id=paper_id,
            review_id=body.review_id,
            is_duplicate=False,
            agent1_label=a1["label"],
            agent2_label=a2["label"],
            final_label=final,
            agent1_reasoning=a1.get("reasoning"),
            agent2_reasoning=a2.get("reasoning"),
            claude_model=MODEL,
        )
        db.add(sd)
        decisions.append(sd)
        # Update paper label
        paper_by_id[paper_id].screening_label = final

    await db.commit()
    for sd in decisions:
        await db.refresh(sd)

    # ── 6. Build response ─────────────────────────────────────────────────
    screened = len(non_dup_papers)
    duplicates_removed = len(papers) - screened
    final_labels = [sd.final_label for sd in decisions]

    return ScreenBatchResponse(
        screened=screened,
        duplicates_removed=duplicates_removed,
        included=final_labels.count("include"),
        excluded=final_labels.count("exclude"),
        uncertain=final_labels.count("uncertain"),
        cohen_kappa=kappa,
        decisions=[ScreeningDecisionOut.model_validate(sd) for sd in decisions],
    )
