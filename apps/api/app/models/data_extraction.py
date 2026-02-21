from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.paper import Paper
    from app.models.review import Review


class DataExtraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Phase 6: structured data extracted from a single included paper."""

    __tablename__ = "data_extractions"

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Structured fields extracted by Claude (JSONB for flexibility)
    extracted_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    extractor_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="complete"
    )  # complete | error

    paper: Mapped[Optional[Paper]] = relationship("Paper")
    review: Mapped[Optional[Review]] = relationship("Review")
