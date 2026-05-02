"""Add persona memory field

Revision ID: 009
Revises: 008
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('personas', sa.Column('memory', sa.JSON(), nullable=True, server_default='[]'))


def downgrade() -> None:
    op.drop_column('personas', 'memory')
