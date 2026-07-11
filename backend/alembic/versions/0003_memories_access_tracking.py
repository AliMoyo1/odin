"""Add access_count and last_accessed_at to memories

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE memories
        ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE memories
        ADD COLUMN last_accessed_at TIMESTAMP WITH TIME ZONE
    """)
    op.execute("""
        CREATE INDEX idx_memories_access ON memories (user_id, access_count, created_at)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_memories_access")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS last_accessed_at")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS access_count")
