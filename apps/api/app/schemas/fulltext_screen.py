from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel


class FulltextScreenRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    # If omitted, auto-selects all include/uncertain papers for the review
    paper_ids: Optional[List[uuid.UUID]] = None
    inclusion_criteria: Optional[str] = None
