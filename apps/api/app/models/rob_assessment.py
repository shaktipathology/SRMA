from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.paper import Paper
    from app.models.review import Review


class RobAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Phase 7: Risk of bias assessment for a single included paper."""

    __tablename__ = "rob_assessments"

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
    # "rob2" for RCTs, "robins-i" for observational studies
    tool: Mapped[str] = mapped_column(String(20), nullable=False, default="rob2")
    # List of {name, judgment, rationale} dicts
    domain_judgments: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    overall_judgment: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # low | some_concerns | high
    assessor_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="complete"
    )  # complete | error

    paper: Mapped[Optional[Paper]] = relationship("Paper")
    review: Mapped[Optional[Review]] = relationship("Review")
