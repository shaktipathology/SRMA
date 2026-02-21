from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.grade_assessment import GradeAssessment
from app.schemas.grade import GradeRequest, GradeResponse, OutcomeGradeOutput
from app.services.grade_engine import assess_outcome

router = APIRouter()


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
async def run_grade(
    body: GradeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GradeResponse:
    """
    Phase 10: Run GRADE certainty-of-evidence assessment for each outcome.

    Pure rule-based engine — no Claude calls.
    Persists GradeAssessment rows to DB if review_id is provided.
    """
    outputs: list[OutcomeGradeOutput] = []

    for outcome in body.outcomes:
        result = assess_outcome(**outcome.model_dump())

        out = OutcomeGradeOutput(
            **outcome.model_dump(),
            starting_certainty=result.starting_certainty,
            certainty=result.certainty,
            downgrade_count=result.downgrade_count,
            upgrade_count=result.upgrade_count,
            rob_decision=result.rob_decision,
            rob_rationale=result.rob_rationale,
            inconsistency_decision=result.inconsistency_decision,
            inconsistency_rationale=result.inconsistency_rationale,
            indirectness_decision=result.indirectness_decision,
            indirectness_rationale=result.indirectness_rationale,
            imprecision_decision=result.imprecision_decision,
            imprecision_rationale=result.imprecision_rationale,
            publication_bias_decision=result.publication_bias_decision,
            publication_bias_rationale=result.publication_bias_rationale,
            upgrade_reasons=result.upgrade_reasons,
            footnotes=result.footnotes,
            grade_symbol=result.grade_symbol,
        )
        outputs.append(out)

        # Persist to DB
        if body.review_id is not None:
            ga = GradeAssessment(
                review_id=body.review_id,
                outcome_name=outcome.outcome_name,
                certainty=result.certainty,
                downgrade_count=result.downgrade_count,
                upgrade_count=result.upgrade_count,
                domain_decisions={
                    "rob": result.rob_decision,
                    "inconsistency": result.inconsistency_decision,
                    "indirectness": result.indirectness_decision,
                    "imprecision": result.imprecision_decision,
                    "publication_bias": result.publication_bias_decision,
                },
                footnotes=result.footnotes,
                importance=outcome.importance,
            )
            db.add(ga)

    if body.review_id is not None:
        await db.commit()

    return GradeResponse(review_id=body.review_id, outcomes=outputs)
