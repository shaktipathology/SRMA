from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.paper import Paper
    from app.models.stats_job import StatsJob
    from app.models.protocol_version import ProtocolVersion
    from app.models.search_query import SearchQuery


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")

    papers: Mapped[List[Paper]] = relationship(
        "Paper", back_populates="review", cascade="all, delete-orphan"
    )
    stats_jobs: Mapped[List[StatsJob]] = relationship(
        "StatsJob", back_populates="review", cascade="all, delete-orphan"
    )
    protocol_versions: Mapped[List[ProtocolVersion]] = relationship(
        "ProtocolVersion", back_populates="review", cascade="all, delete-orphan"
    )
    search_queries: Mapped[List[SearchQuery]] = relationship(
        "SearchQuery", back_populates="review", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} title={self.title!r} status={self.status!r}>"
