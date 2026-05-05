"""Platform column: Enum -> String für dynamische Plattformen.

Revision ID: 021
Revises: 020
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Konvertiere platform Enum-Spalte zu VARCHAR(100)
    # Bestehende Werte ('feedbook', 'threadit') bleiben als Strings erhalten
    op.alter_column(
        "posts",
        "platform",
        type_=sa.String(100),
        existing_type=sa.Enum("feedbook", "threadit", name="platform"),
        existing_nullable=False,
        postgresql_using="platform::text",
    )
    # Enum-Typ droppen (wird nicht mehr gebraucht)
    op.execute("DROP TYPE IF EXISTS platform")


def downgrade() -> None:
    # Enum-Typ neu erstellen
    op.execute("CREATE TYPE platform AS ENUM ('feedbook', 'threadit')")
    op.alter_column(
        "posts",
        "platform",
        type_=sa.Enum("feedbook", "threadit", name="platform", create_type=False),
        existing_type=sa.String(100),
        existing_nullable=False,
        postgresql_using="platform::platform",
    )
