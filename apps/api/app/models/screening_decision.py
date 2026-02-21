from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ScreeningDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "screening_decisions"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Duplicate detection
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_of_paper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Screening stage: "ti_ab" (title/abstract) or "fulltext"
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="ti_ab", index=True)

    # Dual-agent labels: include | exclude | uncertain
    agent1_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    agent2_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    final_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    agent1_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent2_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    claude_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    paper: Mapped[Optional["Paper"]] = relationship("Paper")  # type: ignore[name-defined]
