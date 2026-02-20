from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict


class SearchBuildRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    protocol_version_id: Optional[uuid.UUID] = None
    pico_schema: Dict[str, Any]


class SearchBuildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    review_id: Optional[uuid.UUID] = None
    protocol_version_id: Optional[uuid.UUID] = None
    search_string: Optional[str] = None
    estimated_yield: Optional[int] = None
    database: Optional[str] = None
    claude_model: Optional[str] = None
    rationale: Optional[str] = None
