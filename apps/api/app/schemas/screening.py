from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ScreenBatchRequest(BaseModel):
    paper_ids: List[uuid.UUID]
    review_id: Optional[uuid.UUID] = None
    # Optional free-text criteria handed to both agents
    inclusion_criteria: Optional[str] = None


class ScreeningDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paper_id: uuid.UUID
    review_id: Optional[uuid.UUID] = None
    stage: str = "ti_ab"
    is_duplicate: bool
    duplicate_of_paper_id: Optional[uuid.UUID] = None
    agent1_label: Optional[str] = None
    agent2_label: Optional[str] = None
    final_label: Optional[str] = None
    agent1_reasoning: Optional[str] = None
    agent2_reasoning: Optional[str] = None
    claude_model: Optional[str] = None


class ScreenBatchResponse(BaseModel):
    screened: int                          # papers that went through agents
    duplicates_removed: int
    included: int
    excluded: int
    uncertain: int
    cohen_kappa: Optional[float] = None
    decisions: List[ScreeningDecisionOut]
