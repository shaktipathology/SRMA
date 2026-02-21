from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SofOutcome(BaseModel):
    outcome_name: str
    importance: str
    n_studies: int
    n_participants: int
    effect_measure: str
    effect_size: float
    ci_lower: float
    ci_upper: float
    certainty: str  # high/moderate/low/very_low
    footnotes: List[str] = Field(default_factory=list)


class SofRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    population: str
    intervention: str
    comparator: str
    outcomes: List[SofOutcome]

    @model_validator(mode="after")
    def check_max_outcomes(self) -> "SofRequest":
        if len(self.outcomes) > 7:
            raise ValueError("SoF tables support a maximum of 7 outcomes")
        return self


class SofResponse(BaseModel):
    docx_b64: str
    outcomes_count: int
