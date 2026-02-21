"""add_rob_assessments

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-21 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rob_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool", sa.String(20), nullable=False, server_default="rob2"),
        sa.Column("domain_judgments", postgresql.JSONB(), nullable=True),
        sa.Column("overall_judgment", sa.String(20), nullable=True),
        sa.Column("assessor_model", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="complete"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rob_assessments_review_id", "rob_assessments", ["review_id"])
    op.create_index("ix_rob_assessments_paper_id", "rob_assessments", ["paper_id"])


def downgrade() -> None:
    op.drop_index("ix_rob_assessments_paper_id", table_name="rob_assessments")
    op.drop_index("ix_rob_assessments_review_id", table_name="rob_assessments")
    op.drop_table("rob_assessments")
