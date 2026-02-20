from __future__ import annotations

import uuid
from typing import Optional, Dict, Any

from sqlalchemy import ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SearchQuery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "search_queries"

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    protocol_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("protocol_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pico_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    search_string: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_yield: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    database: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="pubmed")
    claude_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    review: Mapped[Optional["Review"]] = relationship("Review", back_populates="search_queries")  # type: ignore[name-defined]
