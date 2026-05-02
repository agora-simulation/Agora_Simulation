"""Add confidence_assessment and methodology_limitations to analysis_reports

Revision ID: 014
Revises: 013
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('analysis_reports', sa.Column('confidence_assessment', sa.Text(), nullable=True))
    op.add_column('analysis_reports', sa.Column('methodology_limitations', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('analysis_reports', 'methodology_limitations')
    op.drop_column('analysis_reports', 'confidence_assessment')
