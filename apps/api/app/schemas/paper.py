from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PaperRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    review_id: uuid.UUID | None
    title: str | None
    abstract: str | None
    authors: Any | None
    year: int | None
    doi: str | None
    status: str
    screening_label: str | None
    created_at: datetime
    updated_at: datetime


class PaperUpdate(BaseModel):
    screening_label: Literal["include", "exclude", "maybe"] | None = None
    status: str | None = None


class PaperList(BaseModel):
    papers: list[PaperRead]
    total: int
    skip: int
    limit: int
