from __future__ import annotations

import uuid
from typing import List, Literal, Optional

from pydantic import BaseModel, model_validator


class PubBiasRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    study_labels: List[str]
    effect_sizes: List[float]
    standard_errors: List[float]
    measure: Literal["OR", "RR", "MD", "SMD"] = "MD"
    method: Literal["REML", "DL"] = "REML"

    @model_validator(mode="after")
    def _check_lengths(self):
        n = len(self.study_labels)
        if len(self.effect_sizes) != n or len(self.standard_errors) != n:
            raise ValueError(
                "study_labels, effect_sizes, and standard_errors must have equal length"
            )
        if n < 3:
            raise ValueError(
                "At least 3 studies are required for publication bias assessment"
            )
        return self


class PubBiasResponse(BaseModel):
    id: uuid.UUID
    review_id: Optional[uuid.UUID] = None
    phase: int = 9
    status: str = "complete"
    n_studies: int
    egger_pval: float
    trimfill_effect: float
    trimfill_ci_lower: float
    trimfill_ci_upper: float
    funnel_plot: str          # base64 PNG
    # Rule-based concern level derived from egger_pval
    assessment: str           # low_concern | possible_concern | high_concern
    measure: str
    method: str
