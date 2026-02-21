from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GradeAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grade_assessments"

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    outcome_name: Mapped[str] = mapped_column(Text, nullable=False)
    certainty: Mapped[str] = mapped_column(String(20), nullable=False)  # high/moderate/low/very_low
    downgrade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    upgrade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    domain_decisions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    footnotes: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="critical")
    claude_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    review: Mapped[Optional["Review"]] = relationship(  # type: ignore[name-defined]
        "Review", back_populates="grade_assessments"
    )

    def __repr__(self) -> str:
        return f"<GradeAssessment id={self.id} outcome={self.outcome_name!r} certainty={self.certainty!r}>"
