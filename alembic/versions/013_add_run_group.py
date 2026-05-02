"""Add run_group_id and run_index to simulations for multi-run support

Revision ID: 013
Revises: 012
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('simulations', sa.Column('run_group_id', UUID(as_uuid=True), nullable=True))
    op.add_column('simulations', sa.Column('run_index', sa.Integer(), nullable=True))
    op.create_index('ix_simulations_run_group_id', 'simulations', ['run_group_id'])


def downgrade() -> None:
    op.drop_index('ix_simulations_run_group_id', 'simulations')
    op.drop_column('simulations', 'run_index')
    op.drop_column('simulations', 'run_group_id')
