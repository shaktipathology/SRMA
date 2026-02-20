from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.review import Review


class StatsJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stats_jobs"

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    review: Mapped[Optional[Review]] = relationship("Review", back_populates="stats_jobs")

    def __repr__(self) -> str:
        return f"<StatsJob id={self.id} type={self.job_type!r} status={self.status!r}>"
