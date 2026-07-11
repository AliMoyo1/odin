"""Add section_ref to knowledge_chunks; embedding_config_id to knowledge_documents

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE knowledge_chunks
        ADD COLUMN section_ref TEXT
    """)
    op.execute("""
        ALTER TABLE knowledge_documents
        ADD COLUMN embedding_config_id UUID REFERENCES embedding_config(id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN IF EXISTS embedding_config_id")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS section_ref")
