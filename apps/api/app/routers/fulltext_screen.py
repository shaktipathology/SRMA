"""
POST /api/v1/fulltext/screen  —  Phase 5: Full-text eligibility screening.

Workflow:
1. Resolve which papers to screen:
   - explicit paper_ids, OR
   - all papers for the review with screening_label IN ('include', 'uncertain')
     from Phase 3/4 title/abstract screening
2. For each paper, build the full-text string:
   - prefer paper.grobid_tei (GROBID-extracted TEI XML → plain text)
   - fall back to paper.abstract
3. Dual-agent Claude screening (full-text prompts, 6 000-char window)
4. Compute Cohen's κ across the batch
5. Persist new ScreeningDecision rows (stage="fulltext") + update Paper.screening_label
6. Return batch summary
"""
from __future__ import annotations

import asyncio
import re
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.paper import Paper
from app.models.screening_decision import ScreeningDecision
from app.schemas.screening import ScreenBatchResponse, ScreeningDecisionOut
from app.schemas.fulltext_screen import FulltextScreenRequest
from app.services import kappa as kappa_svc
from app.services import screener as screener_svc

router = APIRouter()

MODEL = "claude-sonnet-4-6"

# Labels from Phase 3/4 that advance to full-text review
_ADVANCE_LABELS = {"include", "uncertain"}


def _extract_text(paper: Paper) -> str:
    """Return the best available full text for a paper."""
    if paper.grobid_tei:
        # Strip XML tags to give Claude clean prose
        plain = re.sub(r"<[^>]+>", " ", paper.grobid_tei)
        plain = re.sub(r"\s{2,}", " ", plain).strip()
        return plain
    return paper.abstract or ""


@router.post(
    "/screen",
    response_model=ScreenBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fulltext_screen(
    body: FulltextScreenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScreenBatchResponse:
    """
    Phase 5: Full-text eligibility screening using dual-agent Claude.

    If paper_ids is omitted, automatically screens all papers that were
    marked include or uncertain during Phase 3/4 title/abstract screening.
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
                Paper.screening_label.in_(_ADVANCE_LABELS),
            )
        )
        papers = list(result.scalars().all())
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either review_id (to auto-select papers) or explicit paper_ids.",
        )

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No eligible papers found for full-text screening.",
        )

    # ── 2. Screen each paper ─────────────────────────────────────────────
    async def _screen_one(paper: Paper):
        full_text = _extract_text(paper)
        try:
            a1, a2 = await screener_svc.screen_fulltext_paper(
                title=paper.title,
                full_text=full_text,
                criteria=body.inclusion_criteria,
            )
        except Exception as exc:
            a1 = {"label": "uncertain", "reasoning": f"Agent error: {exc}"}
            a2 = {"label": "uncertain", "reasoning": f"Agent error: {exc}"}
        return paper.id, a1, a2

    screen_results = await asyncio.gather(*[_screen_one(p) for p in papers])

    # ── 3. Cohen's κ ─────────────────────────────────────────────────────
    a1_labels = [r[1]["label"] for r in screen_results]
    a2_labels = [r[2]["label"] for r in screen_results]
    kappa = kappa_svc.compute_kappa(a1_labels, a2_labels)

    # ── 4. Persist decisions ──────────────────────────────────────────────
    paper_by_id = {p.id: p for p in papers}
    decisions: List[ScreeningDecision] = []

    for paper_id, a1, a2 in screen_results:
        final = screener_svc.resolve_final_label(a1["label"], a2["label"])
        sd = ScreeningDecision(
            paper_id=paper_id,
            review_id=body.review_id,
            stage="fulltext",
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
        # Update paper's screening label to the full-text result
        paper_by_id[paper_id].screening_label = final

    await db.commit()
    for sd in decisions:
        await db.refresh(sd)

    # ── 5. Build response ─────────────────────────────────────────────────
    final_labels = [sd.final_label for sd in decisions]
    return ScreenBatchResponse(
        screened=len(papers),
        duplicates_removed=0,
        included=final_labels.count("include"),
        excluded=final_labels.count("exclude"),
        uncertain=final_labels.count("uncertain"),
        cohen_kappa=kappa,
        decisions=[ScreeningDecisionOut.model_validate(sd) for sd in decisions],
    )
