from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ExtractRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    # If omitted, auto-selects all screening_label="include" papers for the review
    paper_ids: Optional[List[uuid.UUID]] = None
    # Optional free-text extraction template / instructions for Claude
    extraction_template: Optional[str] = None


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paper_id: uuid.UUID
    review_id: Optional[uuid.UUID] = None
    status: str
    extracted_data: Optional[Dict[str, Any]] = None
    extractor_model: Optional[str] = None


class ExtractBatchResponse(BaseModel):
    extracted: int
    successful: int
    failed: int
    extractions: List[ExtractionOut]
