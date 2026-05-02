"""Add persona_type and entity_subtype to personas

Revision ID: 012
Revises: 011
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('personas', sa.Column('persona_type', sa.String(30), server_default='individual'))
    op.add_column('personas', sa.Column('entity_subtype', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('personas', 'entity_subtype')
    op.drop_column('personas', 'persona_type')
