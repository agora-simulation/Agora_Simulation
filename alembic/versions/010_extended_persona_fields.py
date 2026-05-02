"""Add extended persona fields (Big Five + demographics)

Revision ID: 010
Revises: 009
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('personas', sa.Column('education_level', sa.String(50), nullable=True))
    op.add_column('personas', sa.Column('income_bracket', sa.String(30), nullable=True))
    op.add_column('personas', sa.Column('family_status', sa.String(30), nullable=True))
    op.add_column('personas', sa.Column('political_leaning', sa.String(30), nullable=True))
    op.add_column('personas', sa.Column('media_consumption', sa.JSON(), nullable=True, server_default='[]'))
    op.add_column('personas', sa.Column('tech_affinity', sa.Float(), nullable=True, server_default='0.5'))
    op.add_column('personas', sa.Column('personality_traits', sa.JSON(), nullable=True, server_default='{}'))


def downgrade() -> None:
    op.drop_column('personas', 'personality_traits')
    op.drop_column('personas', 'tech_affinity')
    op.drop_column('personas', 'media_consumption')
    op.drop_column('personas', 'political_leaning')
    op.drop_column('personas', 'family_status')
    op.drop_column('personas', 'income_bracket')
    op.drop_column('personas', 'education_level')
