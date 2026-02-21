"""add_data_extractions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-21 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extracted_data", postgresql.JSONB(), nullable=True),
        sa.Column("extractor_model", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="complete"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_data_extractions_review_id", "data_extractions", ["review_id"])
    op.create_index("ix_data_extractions_paper_id", "data_extractions", ["paper_id"])


def downgrade() -> None:
    op.drop_index("ix_data_extractions_paper_id", table_name="data_extractions")
    op.drop_index("ix_data_extractions_review_id", table_name="data_extractions")
    op.drop_table("data_extractions")
