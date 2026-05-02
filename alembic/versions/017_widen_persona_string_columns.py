"""Widen persona string columns to prevent truncation errors

Revision ID: 017
Revises: 016
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('personas', 'age', type_=sa.String(50))
    op.alter_column('personas', 'persona_type', type_=sa.String(50))
    op.alter_column('personas', 'entity_subtype', type_=sa.String(200))
    op.alter_column('personas', 'education_level', type_=sa.String(100))
    op.alter_column('personas', 'income_bracket', type_=sa.String(50))
    op.alter_column('personas', 'family_status', type_=sa.String(100))
    op.alter_column('personas', 'political_leaning', type_=sa.String(100))


def downgrade() -> None:
    op.alter_column('personas', 'age', type_=sa.String(10))
    op.alter_column('personas', 'persona_type', type_=sa.String(30))
    op.alter_column('personas', 'entity_subtype', type_=sa.String(100))
    op.alter_column('personas', 'education_level', type_=sa.String(30))
    op.alter_column('personas', 'income_bracket', type_=sa.String(30))
    op.alter_column('personas', 'family_status', type_=sa.String(30))
    op.alter_column('personas', 'political_leaning', type_=sa.String(30))
