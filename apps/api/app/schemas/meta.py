from __future__ import annotations

import uuid
from typing import List, Literal, Optional

from pydantic import BaseModel, model_validator


class MetaRunRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    study_labels: List[str]
    effect_sizes: List[float]
    standard_errors: List[float]
    measure: Literal["OR", "RR", "MD", "SMD"] = "MD"
    method: Literal["REML", "DL"] = "REML"

    @model_validator(mode="after")
    def check_lengths(self) -> "MetaRunRequest":
        n = len(self.study_labels)
        if len(self.effect_sizes) != n or len(self.standard_errors) != n:
            raise ValueError(
                "study_labels, effect_sizes, and standard_errors must have equal length"
            )
        if n < 2:
            raise ValueError("At least 2 studies are required for pooling")
        return self


class MetaRunResponse(BaseModel):
    id: uuid.UUID
    review_id: Optional[uuid.UUID] = None
    phase: int = 8
    status: str = "complete"

    # Pooled statistics from the stats worker
    pooled_effect: float
    ci_lower: float
    ci_upper: float
    i2: float
    tau2: float
    q_pval: float
    pred_lower: Optional[float] = None
    pred_upper: Optional[float] = None

    # Base64-encoded forest plot PNG
    forest_plot: str

    # Echo back inputs for traceability
    measure: str
    method: str
    n_studies: int
