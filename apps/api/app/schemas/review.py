from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ReviewCreate(BaseModel):
    title: str
    description: str | None = None


class ReviewUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["draft", "active", "completed", "archived"] | None = None


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ReviewList(BaseModel):
    reviews: list[ReviewRead]
    total: int
    skip: int
    limit: int
