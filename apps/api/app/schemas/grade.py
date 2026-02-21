from __future__ import annotations

import uuid
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class OutcomeGradeInput(BaseModel):
    outcome_name: str
    study_design: Literal["rct", "observational"]
    n_studies: int
    total_n: int
    rob_summary: Literal["low", "some_concerns", "high"]
    i2: float = Field(ge=0, le=100)
    prediction_interval_crosses_null: bool
    directness: Literal["direct", "minor_concerns", "major_concerns"]
    ci_lower: float
    ci_upper: float
    effect_size: float
    measure: Literal["OR", "RR", "MD", "SMD"]
    n_studies_for_funnel: int
    egger_pval: Optional[float] = None
    large_effect: bool = False
    dose_response: bool = False
    residual_confounding_direction: Optional[Literal["towards_null", "away_from_null"]] = None
    importance: Literal["critical", "important", "not_important"] = "critical"


class GradeRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    outcomes: List[OutcomeGradeInput]


class OutcomeGradeOutput(OutcomeGradeInput):
    starting_certainty: str
    certainty: str
    downgrade_count: int
    upgrade_count: int

    # Per-domain decisions and rationale
    rob_decision: int
    rob_rationale: str
    inconsistency_decision: int
    inconsistency_rationale: str
    indirectness_decision: int
    indirectness_rationale: str
    imprecision_decision: int
    imprecision_rationale: str
    publication_bias_decision: int
    publication_bias_rationale: str

    upgrade_reasons: List[str]
    footnotes: List[str]
    grade_symbol: str


class GradeResponse(BaseModel):
    review_id: Optional[uuid.UUID] = None
    outcomes: List[OutcomeGradeOutput]
