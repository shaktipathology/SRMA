from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel


class StubRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    payload: Dict[str, Any] = {}


class StubResponse(BaseModel):
    phase: int
    status: str
    id: uuid.UUID
    message: str
