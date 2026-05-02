"""Add persona_conversations table

Revision ID: 011
Revises: 010
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'persona_conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('persona_id', UUID(as_uuid=True), sa.ForeignKey('personas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('messages', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_persona_conversations_persona', 'persona_conversations', ['persona_id'])


def downgrade() -> None:
    op.drop_index('idx_persona_conversations_persona', table_name='persona_conversations')
    op.drop_table('persona_conversations')
