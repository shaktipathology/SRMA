from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PhaseResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "phase_results"

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    phase_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    phase_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="stub")  # "complete" | "stub"
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    review: Mapped[Optional["Review"]] = relationship(  # type: ignore[name-defined]
        "Review", back_populates="phase_results"
    )

    def __repr__(self) -> str:
        return f"<PhaseResult id={self.id} phase={self.phase_number} status={self.status!r}>"
