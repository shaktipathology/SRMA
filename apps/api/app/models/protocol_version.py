from __future__ import annotations

import uuid
from typing import Optional, Dict, Any

from sqlalchemy import ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProtocolVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "protocol_versions"

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    pico_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    minio_prefix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claude_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    review: Mapped[Optional["Review"]] = relationship("Review", back_populates="protocol_versions")  # type: ignore[name-defined]
