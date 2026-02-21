"""add_grade_assessments_and_phase_results

Revision ID: a1b2c3d4e5f6
Revises: 54865d5dbab7
Create Date: 2026-02-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '54865d5dbab7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- grade_assessments ---
    op.create_table(
        'grade_assessments',
        sa.Column('review_id', sa.UUID(), nullable=True),
        sa.Column('outcome_name', sa.Text(), nullable=False),
        sa.Column('certainty', sa.String(length=20), nullable=False),
        sa.Column('downgrade_count', sa.Integer(), nullable=False),
        sa.Column('upgrade_count', sa.Integer(), nullable=False),
        sa.Column('domain_decisions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('footnotes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('importance', sa.String(length=20), nullable=False),
        sa.Column('claude_model', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_grade_assessments_review_id'),
        'grade_assessments',
        ['review_id'],
        unique=False,
    )

    # --- phase_results ---
    op.create_table(
        'phase_results',
        sa.Column('review_id', sa.UUID(), nullable=True),
        sa.Column('phase_number', sa.Integer(), nullable=False),
        sa.Column('phase_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_phase_results_review_id'),
        'phase_results',
        ['review_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_phase_results_phase_number'),
        'phase_results',
        ['phase_number'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_phase_results_phase_number'), table_name='phase_results')
    op.drop_index(op.f('ix_phase_results_review_id'), table_name='phase_results')
    op.drop_table('phase_results')
    op.drop_index(op.f('ix_grade_assessments_review_id'), table_name='grade_assessments')
    op.drop_table('grade_assessments')
