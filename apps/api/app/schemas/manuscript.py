from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel


class ManuscriptRequest(BaseModel):
    review_id: uuid.UUID
    title: Optional[str] = None
    target_journal: Optional[str] = None
    use_claude_narratives: bool = True


class ManuscriptResponse(BaseModel):
    docx_b64: str
    sections_included: List[str]
    missing_phase_data: List[str]
    word_count: int
