from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.phase_result import PhaseResult
from app.schemas.meta import MetaRunRequest, MetaRunResponse
from app.services import stats_worker as stats_worker_svc

router = APIRouter()


@router.post("", response_model=MetaRunResponse, status_code=status.HTTP_201_CREATED)
async def run_meta_analysis(
    body: MetaRunRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetaRunResponse:
    """
    Phase 8: Run a pooled meta-analysis via the Stats Worker (R/metafor).

    Calls POST /pool on the stats-worker microservice, persists the full
    result (including forest plot) as a PhaseResult row, and returns
    pooled statistics and the base64-encoded forest plot PNG.
    """
    pool_payload = {
        "study_labels": body.study_labels,
        "effect_sizes": body.effect_sizes,
        "standard_errors": body.standard_errors,
        "measure": body.measure,
        "method": body.method,
    }

    try:
        pool_result = await stats_worker_svc.run_pool(pool_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stats worker error: {exc}",
        ) from exc

    # Persist to DB
    result_data = {
        **pool_payload,
        "pooled_effect": pool_result["pooled_effect"],
        "ci_lower": pool_result["ci_lower"],
        "ci_upper": pool_result["ci_upper"],
        "i2": pool_result["i2"],
        "tau2": pool_result["tau2"],
        "q_pval": pool_result["q_pval"],
        "pred_lower": pool_result.get("pred_lower"),
        "pred_upper": pool_result.get("pred_upper"),
        # Store forest_plot separately — large blob, kept in result_data
        "forest_plot": pool_result["forest_plot"],
    }

    pr = PhaseResult(
        review_id=body.review_id,
        phase_number=8,
        phase_name="Meta-analysis",
        status="complete",
        result_data=result_data,
    )
    db.add(pr)
    await db.commit()
    await db.refresh(pr)

    return MetaRunResponse(
        id=pr.id,
        review_id=body.review_id,
        pooled_effect=pool_result["pooled_effect"],
        ci_lower=pool_result["ci_lower"],
        ci_upper=pool_result["ci_upper"],
        i2=pool_result["i2"],
        tau2=pool_result["tau2"],
        q_pval=pool_result["q_pval"],
        pred_lower=pool_result.get("pred_lower"),
        pred_upper=pool_result.get("pred_upper"),
        forest_plot=pool_result["forest_plot"],
        measure=body.measure,
        method=body.method,
        n_studies=len(body.study_labels),
    )
