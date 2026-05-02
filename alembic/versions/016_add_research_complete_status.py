"""Add research_complete status to SimulationStatus enum

Revision ID: 016
Revises: 015
Create Date: 2026-05-02
"""
from alembic import op

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE simulationstatus ADD VALUE IF NOT EXISTS 'research_complete' AFTER 'researching'")


def downgrade() -> None:
    pass  # Cannot remove enum value in PostgreSQL
