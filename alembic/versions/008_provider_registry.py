"""Provider-Registry Tabelle + provider_config JSON-Spalte in simulations

Revision ID: 008
Revises: 007
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'llm_providers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('provider_type', sa.String(32), nullable=False),
        sa.Column('api_key_encrypted', sa.String(2048), nullable=False),
        sa.Column('base_url', sa.String(2048), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.add_column('simulations', sa.Column('provider_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('simulations', 'provider_config')
    op.drop_table('llm_providers')
