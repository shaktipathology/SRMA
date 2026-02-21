from __future__ import annotations

import uuid
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PrismaItem(BaseModel):
    item_number: int
    domain: str
    description: str
    status: Literal["satisfied", "partial", "missing", "not_applicable"]
    notes: Optional[str] = None


class PrismaCheckRequest(BaseModel):
    review_id: uuid.UUID


class PrismaCheckResponse(BaseModel):
    review_id: uuid.UUID
    total_items: int = Field(default=27)
    satisfied: int
    partial: int
    missing: int
    not_applicable: int
    is_compliant: bool
    checklist: List[PrismaItem]
