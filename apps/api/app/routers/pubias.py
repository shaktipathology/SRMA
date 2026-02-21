"""
POST /api/v1/pubias/assess  —  Phase 9: Publication bias assessment.

Workflow:
1. Call stats worker POST /funnel (Egger's test + trim-and-fill + funnel plot)
2. Derive concern level from egger_pval:
   pval < 0.05  → "high_concern"
   pval < 0.10  → "possible_concern"
   else         → "low_concern"
3. Persist PhaseResult(phase_number=9, status="complete")
4. Return PubBiasResponse
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.phase_result import PhaseResult
from app.schemas.pubias import PubBiasRequest, PubBiasResponse
from app.services import stats_worker as stats_worker_svc

router = APIRouter()


def _concern_level(egger_pval: float) -> str:
    if egger_pval < 0.05:
        return "high_concern"
    if egger_pval < 0.10:
        return "possible_concern"
    return "low_concern"


@router.post(
    "/assess",
    response_model=PubBiasResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assess_publication_bias(
    body: PubBiasRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PubBiasResponse:
    """
    Phase 9: Publication bias assessment via Egger's test and trim-and-fill
    (R/metafor stats worker).

    Requires ≥3 studies. Returns Egger p-value, trim-and-fill adjusted estimate,
    base64 funnel plot PNG, and a rule-based concern level.
    """
    funnel_payload = {
        "study_labels": body.study_labels,
        "effect_sizes": body.effect_sizes,
        "standard_errors": body.standard_errors,
        "measure": body.measure,
        "method": body.method,
    }

    try:
        result = await stats_worker_svc.run_funnel(funnel_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stats worker error: {exc}",
        ) from exc

    assessment = _concern_level(result["egger_pval"])

    result_data = {
        **funnel_payload,
        "egger_pval": result["egger_pval"],
        "trimfill_effect": result["trimfill_effect"],
        "trimfill_ci_lower": result["trimfill_ci_lower"],
        "trimfill_ci_upper": result["trimfill_ci_upper"],
        "funnel_plot": result["funnel_plot"],
        "assessment": assessment,
    }

    pr = PhaseResult(
        review_id=body.review_id,
        phase_number=9,
        phase_name="Publication bias assessment",
        status="complete",
        result_data=result_data,
    )
    db.add(pr)
    await db.commit()
    await db.refresh(pr)

    return PubBiasResponse(
        id=pr.id,
        review_id=body.review_id,
        n_studies=len(body.study_labels),
        egger_pval=result["egger_pval"],
        trimfill_effect=result["trimfill_effect"],
        trimfill_ci_lower=result["trimfill_ci_lower"],
        trimfill_ci_upper=result["trimfill_ci_upper"],
        funnel_plot=result["funnel_plot"],
        assessment=assessment,
        measure=body.measure,
        method=body.method,
    )
