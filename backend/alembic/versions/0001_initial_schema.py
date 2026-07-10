"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Enum types
    op.execute("""
        CREATE TYPE task_status AS ENUM (
            'backlog', 'todo', 'in_progress', 'blocked', 'done', 'cancelled'
        )
    """)
    op.execute("""
        CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical')
    """)
    op.execute("""
        CREATE TYPE memory_type AS ENUM ('explicit', 'implicit')
    """)
    op.execute("""
        CREATE TYPE notification_category AS ENUM ('task', 'system', 'hermes', 'whatsapp')
    """)
    op.execute("""
        CREATE TYPE circuit_state AS ENUM ('closed', 'open', 'half_open')
    """)

    # embedding_config (no UNIQUE on is_active column; partial index below)
    op.execute("""
        CREATE TABLE embedding_config (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR(50) NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            dimensions INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # users
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            totp_secret_enc TEXT,
            totp_enabled BOOLEAN DEFAULT FALSE,
            totp_locked_until TIMESTAMP WITH TIME ZONE,
            totp_fail_count INTEGER DEFAULT 0,
            timezone VARCHAR(64) DEFAULT 'UTC',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # sessions
    op.execute("""
        CREATE TABLE sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            refresh_token_hash VARCHAR(255) NOT NULL,
            user_agent TEXT,
            ip_address VARCHAR(45),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # ws_tickets
    op.execute("""
        CREATE TABLE ws_tickets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            used BOOLEAN DEFAULT FALSE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # projects
    op.execute("""
        CREATE TABLE projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            workspace_path TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # tasks
    op.execute("""
        CREATE TABLE tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            status task_status NOT NULL DEFAULT 'backlog',
            priority task_priority NOT NULL DEFAULT 'medium',
            due_date TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            tags JSONB,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # subtasks
    op.execute("""
        CREATE TABLE subtasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            done BOOLEAN DEFAULT FALSE,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # task_changelog
    op.execute("""
        CREATE TABLE task_changelog (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            field_name VARCHAR(100) NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # conversations
    op.execute("""
        CREATE TABLE conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
            title VARCHAR(500),
            summary TEXT,
            message_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # messages
    op.execute("""
        CREATE TABLE messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT,
            content_blocks JSONB,
            token_count INTEGER,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # knowledge_documents (with deliberate extra columns indexed_at, content_sha256)
    op.execute("""
        CREATE TABLE knowledge_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
            file_path TEXT NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            mime_type VARCHAR(100),
            file_size INTEGER,
            chunk_count INTEGER DEFAULT 0,
            processed BOOLEAN DEFAULT FALSE,
            indexed_at TIMESTAMP WITH TIME ZONE,
            content_sha256 VARCHAR(64),
            chunk_config JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # knowledge_chunks
    op.execute("""
        CREATE TABLE knowledge_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            page_number INTEGER,
            embedding VECTOR(1536),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # memories
    op.execute("""
        CREATE TABLE memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
            memory_type memory_type NOT NULL,
            key VARCHAR(500),
            value TEXT NOT NULL,
            embedding VECTOR(1536),
            confidence FLOAT,
            approved BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # activity_log
    op.execute("""
        CREATE TABLE activity_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            org_id VARCHAR(255),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100),
            resource_id VARCHAR(255),
            metadata JSONB,
            ip_address VARCHAR(45),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # notifications
    op.execute("""
        CREATE TABLE notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            body TEXT,
            category notification_category NOT NULL,
            read BOOLEAN DEFAULT FALSE,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # integration_configs
    op.execute("""
        CREATE TABLE integration_configs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            credentials_enc TEXT,
            config JSONB,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # tool_approvals
    op.execute("""
        CREATE TABLE tool_approvals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tool_name VARCHAR(100) NOT NULL,
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            auto_approve BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT uq_tool_approvals UNIQUE (user_id, tool_name, project_id)
        )
    """)

    # llm_provider_health
    op.execute("""
        CREATE TABLE llm_provider_health (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR(50) UNIQUE NOT NULL,
            circuit_state circuit_state NOT NULL DEFAULT 'closed',
            consecutive_failures INTEGER DEFAULT 0,
            circuit_opened_at TIMESTAMP WITH TIME ZONE,
            last_success_at TIMESTAMP WITH TIME ZONE,
            last_failure_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # backups
    op.execute("""
        CREATE TABLE backups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename VARCHAR(500) NOT NULL,
            size_bytes INTEGER,
            sha256 VARCHAR(64),
            offsite_synced BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # Partial unique index on embedding_config (PLAN-00 deliberate delta)
    op.execute("""
        CREATE UNIQUE INDEX one_active_embedding_config
        ON embedding_config (is_active)
        WHERE is_active = TRUE
    """)

    # Seed default embedding config
    op.execute("""
        INSERT INTO embedding_config (provider, model_name, dimensions, is_active)
        VALUES ('openai', 'text-embedding-3-small', 1536, TRUE)
    """)

    # B-tree indexes
    op.execute("CREATE INDEX idx_tasks_user_status ON tasks (user_id, status)")
    op.execute("CREATE INDEX idx_tasks_project ON tasks (project_id)")
    op.execute("CREATE INDEX idx_messages_conversation ON messages (conversation_id, created_at)")
    op.execute("CREATE INDEX idx_memories_user ON memories (user_id, memory_type)")
    op.execute("CREATE INDEX idx_activity_log_user ON activity_log (user_id, created_at DESC)")
    op.execute("CREATE INDEX idx_notifications_user_unread ON notifications (user_id, read)")
    op.execute("CREATE INDEX idx_knowledge_docs_user ON knowledge_documents (user_id)")
    op.execute("CREATE INDEX idx_sessions_user ON sessions (user_id)")
    op.execute("CREATE INDEX idx_ws_tickets_expires ON ws_tickets (expires_at)")

    # GIN full-text index on messages
    op.execute("""
        CREATE INDEX idx_messages_content_gin
        ON messages
        USING gin (to_tsvector('english', coalesce(content, '')))
    """)

    # HNSW vector indexes
    op.execute("""
        CREATE INDEX idx_kb_vector_cosine
        ON knowledge_chunks
        USING hnsw (embedding vector_cosine_ops)
    """)
    op.execute("""
        CREATE INDEX idx_memories_vector_cosine
        ON memories
        USING hnsw (embedding vector_cosine_ops)
    """)

    # updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Apply trigger to tables with updated_at
    for table in [
        "users", "projects", "tasks", "conversations",
        "knowledge_documents", "memories", "integration_configs",
        "tool_approvals", "llm_provider_health",
    ]:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """)


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for initial schema")
