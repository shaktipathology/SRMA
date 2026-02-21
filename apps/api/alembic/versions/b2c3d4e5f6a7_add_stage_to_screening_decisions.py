"""add_stage_to_screening_decisions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-21 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "screening_decisions",
        sa.Column(
            "stage",
            sa.String(length=20),
            nullable=False,
            server_default="ti_ab",
        ),
    )
    op.create_index(
        op.f("ix_screening_decisions_stage"),
        "screening_decisions",
        ["stage"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_screening_decisions_stage"), table_name="screening_decisions"
    )
    op.drop_column("screening_decisions", "stage")
