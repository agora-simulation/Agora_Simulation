"""Add market_contexts table, research_mode to simulations, researching status

Revision ID: 015
Revises: 014
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Neuen Status 'researching' zum Enum hinzufügen
    op.execute("ALTER TYPE simulationstatus ADD VALUE IF NOT EXISTS 'researching' BEFORE 'running'")

    # research_mode Spalte auf simulations
    op.add_column('simulations', sa.Column('research_mode', sa.String(10), server_default='quick', nullable=False))

    # MarketContext Tabelle
    op.create_table(
        'market_contexts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.id'), nullable=False, unique=True),
        sa.Column('macro_context', sa.Text(), nullable=True),
        sa.Column('industry_context', sa.Text(), nullable=True),
        sa.Column('target_group_context', sa.Text(), nullable=True),
        sa.Column('raw_sources', sa.JSON(), nullable=True),
        sa.Column('prompt_summary', sa.Text(), nullable=True),
        sa.Column('research_queries', sa.JSON(), nullable=True),
        sa.Column('research_mode', sa.String(10), server_default='deep'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('market_contexts')
    op.drop_column('simulations', 'research_mode')
    # Note: Cannot remove enum value in PostgreSQL without recreating the type
