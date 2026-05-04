"""Add research execution fields (provider, model, prompt, result).

Revision ID: 019
Revises: 018
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_snapshots", sa.Column("provider_id", UUID(as_uuid=True), nullable=True))
    op.add_column("research_snapshots", sa.Column("model", sa.String(100), nullable=True))
    op.add_column("research_snapshots", sa.Column("prompt", sa.Text(), nullable=True))
    op.add_column("research_snapshots", sa.Column("system_prompt", sa.Text(), nullable=True))
    op.add_column("research_snapshots", sa.Column("result", sa.Text(), nullable=True))
    op.add_column("research_snapshots", sa.Column("template_id", UUID(as_uuid=True), nullable=True))
    op.add_column("research_snapshots", sa.Column("temperature", sa.Float(), nullable=True))
    op.add_column("research_snapshots", sa.Column("max_tokens", sa.Integer(), server_default="4096", nullable=True))
    op.add_column("research_snapshots", sa.Column("execution_started_at", sa.DateTime(), nullable=True))
    op.add_column("research_snapshots", sa.Column("execution_finished_at", sa.DateTime(), nullable=True))
    op.add_column("research_snapshots", sa.Column("error", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_research_provider",
        "research_snapshots", "llm_providers",
        ["provider_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_research_template",
        "research_snapshots", "templates",
        ["template_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_research_template", "research_snapshots", type_="foreignkey")
    op.drop_constraint("fk_research_provider", "research_snapshots", type_="foreignkey")
    op.drop_column("research_snapshots", "error")
    op.drop_column("research_snapshots", "execution_finished_at")
    op.drop_column("research_snapshots", "execution_started_at")
    op.drop_column("research_snapshots", "max_tokens")
    op.drop_column("research_snapshots", "temperature")
    op.drop_column("research_snapshots", "template_id")
    op.drop_column("research_snapshots", "result")
    op.drop_column("research_snapshots", "system_prompt")
    op.drop_column("research_snapshots", "prompt")
    op.drop_column("research_snapshots", "model")
    op.drop_column("research_snapshots", "provider_id")
