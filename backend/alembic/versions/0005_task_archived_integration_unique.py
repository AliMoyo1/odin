"""Add archived task status; unique constraint on integration_configs

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'archived'")
    op.execute("""
        ALTER TABLE integration_configs
        ADD CONSTRAINT uq_integration_user_service UNIQUE (user_id, name)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE integration_configs DROP CONSTRAINT IF EXISTS uq_integration_user_service")
    # PostgreSQL does not support removing enum values; no downgrade for the enum change
