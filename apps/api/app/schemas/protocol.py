from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict


class PicoSchema(BaseModel):
    population: str
    intervention: str
    comparator: str
    outcomes: List[str]
    study_designs: List[str]


class ProtocolRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    research_question: str


class ProtocolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    review_id: Optional[uuid.UUID] = None
    version: int
    research_question: str
    pico_schema: Optional[Dict[str, Any]] = None
    minio_prefix: Optional[str] = None
    claude_model: Optional[str] = None
