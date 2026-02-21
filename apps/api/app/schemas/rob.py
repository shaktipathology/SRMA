from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class RobAssessRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    # If omitted, auto-selects screening_label="include" papers for the review
    paper_ids: Optional[List[uuid.UUID]] = None
    # Which RoB tool to apply
    tool: Literal["rob2", "robins-i"] = "rob2"


class DomainJudgment(BaseModel):
    name: str
    judgment: str  # low | some_concerns | high
    rationale: str


class RobAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paper_id: uuid.UUID
    review_id: Optional[uuid.UUID] = None
    tool: str
    domain_judgments: Optional[List[Any]] = None
    overall_judgment: Optional[str] = None
    assessor_model: Optional[str] = None
    status: str


class RobBatchResponse(BaseModel):
    assessed: int
    successful: int
    failed: int
    low_risk: int
    some_concerns: int
    high_risk: int
    assessments: List[RobAssessmentOut]
