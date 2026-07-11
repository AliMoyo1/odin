"""Add metadata JSONB column to memories

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE memories
        ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS metadata")
