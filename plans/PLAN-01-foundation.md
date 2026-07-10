# PLAN-01: Foundation, Docker Stack, Database Schema, Observability

Goal: a running dev stack (API + Postgres/pgvector + Redis + Celery worker + beat) with the complete database schema migrated, config loading, structured JSON logging with request IDs, `/health/live`, `/health/ready`, and `/metrics`. After this plan, every other plan has a home.

Spec references: SPEC Doc 03 (3.4 observability), Doc 04, Doc 05, Doc 08 (full DDL), Doc 16 (16.1 dev compose, 16.3 env template).

## Files to create

```
.gitignore
.env.example
docker-compose.dev.yml
backend\requirements.txt
backend\requirements-rerank.txt
backend\Dockerfile.dev
backend\app\__init__.py
backend\app\config.py
backend\app\logging_config.py
backend\app\middleware.py
backend\app\db.py
backend\app\metrics.py
backend\app\main.py
backend\app\models\__init__.py
backend\app\models\models.py
backend\app\routers\__init__.py
backend\app\routers\health.py
backend\workers\__init__.py
backend\workers\celery_app.py
backend\alembic.ini
backend\alembic\env.py
backend\alembic\versions\0001_initial_schema.py
workspace\  (with subfolders Inbox, Projects, Knowledge, Learning, Outputs, each containing an empty .gitkeep)
README.md
```

## Steps in order

### Step 1: git init and hygiene

Run: `git init "C:\Users\isadmin\Desktop\Odin"`

Create `.gitignore` containing at minimum:

```
.env
keys/
workspace/
__pycache__/
*.pyc
node_modules/
dist/
.pytest_cache/
backups/
```

### Step 2: .env.example

Create `.env.example` with every variable below, placeholder values only. Copy it to `.env` afterwards and fill only DB values for dev (the rest can stay blank until their plan needs them).

```
# Core
ENVIRONMENT=dev
SECRET_KEY=REPLACE_WITH_64_CHAR_HEX
ENCRYPTION_KEY=REPLACE_WITH_BASE64_32_BYTES
JWT_PRIVATE_KEY_PATH=/keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/keys/jwt_public.pem

# Database and cache
DB_USER=odin
DB_PASSWORD=odin_dev_password
DB_NAME=odin
DATABASE_URL=postgresql+asyncpg://odin:odin_dev_password@database-node:5432/odin
REDIS_URL=redis://redis-broker:6379/0

# Workspace root inside containers
WORKSPACE_ROOT=/data/ODIN

# LLM provider chain (PLAN-04)
ANTHROPIC_API_KEY=
HERMES_MODEL_ANTHROPIC=claude-opus-4-8
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b

# Embeddings (PLAN-05)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
RERANK_ENABLED=0

# WhatsApp (PLAN-07)
WHATSAPP_APP_SECRET=
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ALLOWED_NUMBER=
WA_DRY_RUN=1

# SMTP for password reset (PLAN-02, optional in dev)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

# Integrations (PLAN-09)
CLOUDFLARE_API_TOKEN=
HETZNER_API_TOKEN=
GITHUB_TOKEN=

# Backups (PLAN-09)
BACKUP_LOCAL_DIR=/backups
BACKUP_OFFSITE_REMOTE=
BACKUP_RETENTION_DAYS=30

# Watcher (PLAN-05)
WATCHER_FORCE_POLLING=1

# CORS
CORS_ALLOWED_ORIGIN=http://localhost:5173
```

### Step 3: requirements

`backend\requirements.txt` (base, no torch):

```
fastapi
uvicorn[standard]
pydantic-settings
sqlalchemy[asyncio]>=2.0
asyncpg
psycopg2-binary
alembic
pgvector
redis
celery
structlog
prometheus-client
httpx
python-multipart
PyJWT[crypto]
bcrypt==4.0.1
passlib[bcrypt]==1.7.4
pyotp
anthropic
openai
google-genai
tiktoken
pdfplumber
python-docx
beautifulsoup4
watchdog
pytest
pytest-asyncio
websockets
```

`backend\requirements-rerank.txt` (installed only when RERANK_ENABLED=1, see PLAN-05):

```
sentence-transformers
```

### Step 4: Dockerfile.dev

`backend\Dockerfile.dev`. Use separate RUN lines, do not chain with `&&`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update
RUN apt-get install -y --no-install-recommends ffmpeg postgresql-client curl
RUN rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Step 5: docker-compose.dev.yml

```yaml
services:
  gateway-api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./workspace:/data/ODIN
      - ./keys:/keys:ro
    env_file: .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - database-node
      - redis-broker

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A workers.celery_app worker --loglevel=info
    volumes:
      - ./backend:/app
      - ./workspace:/data/ODIN
      - ./backups:/backups
    env_file: .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - redis-broker
      - database-node

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A workers.celery_app beat --loglevel=info
    volumes:
      - ./backend:/app
    env_file: .env
    depends_on:
      - redis-broker

  database-node:
    image: pgvector/pgvector:pg16
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - odin_db_data:/var/lib/postgresql/data

  redis-broker:
    image: redis:7-alpine
    ports:
      - "6380:6379"

volumes:
  odin_db_data:
```

Notes baked into this file: host port 5433 (not 5432) and 6380 (not 6379) to avoid colliding with anything ThemisIQ-related already on the machine. Containers talk to `database-node:5432` internally regardless.

### Step 6: config.py

`backend\app\config.py`: a `pydantic_settings.BaseSettings` class named `Settings` with one typed field per `.env.example` variable (str, int, bool as appropriate; bools parse "0"/"1"). Module-level `settings = Settings()`. Everything else imports `from app.config import settings`. No `os.environ` reads anywhere else in the codebase.

### Step 7: logging, request IDs, metrics

- `logging_config.py`: configure structlog to emit single-line JSON to stdout with keys `timestamp`, `level`, `service`, `request_id`, `user_id`, `message`, `duration_ms` (SPEC 3.4). Provide `get_logger(service: str)`.
- `middleware.py`: an ASGI middleware that reads `X-Request-ID` from the inbound request or generates a uuid4, stores it in a `contextvars.ContextVar`, binds it into structlog, sets it on the response header, and logs one line per request with method, path, status, duration_ms.
- `metrics.py`: prometheus-client counters and histograms: `http_requests_total{path,method,status}`, `http_request_duration_seconds{path}`, `ws_connections_active`, `llm_calls_total{provider,outcome}`, `llm_call_duration_seconds{provider}`, `celery_queue_depth`. Expose `GET /metrics` returning `generate_latest()` with the correct content type.

### Step 8: db.py and models

- `db.py`: async engine from `settings.DATABASE_URL`, `async_session` factory, `get_session` FastAPI dependency.
- `models\models.py`: SQLAlchemy 2.0 declarative models mirroring SPEC 8.2 exactly, one class per table (19 tables: users, sessions, ws_tickets, projects, tasks, subtasks, task_changelog, conversations, messages, knowledge_documents, knowledge_chunks, memories, activity_log, notifications, integration_configs, tool_approvals, llm_provider_health, backups, embedding_config). Postgres enums declared with `create_type=False` because the migration creates them. Vector columns use `pgvector.sqlalchemy.Vector(1536)`.

### Step 9: the initial Alembic migration

- `alembic init` layout with `alembic.ini` pointing `script_location = alembic`.
- In `alembic\env.py`, use a synchronous engine. Derive the URL with exactly: `url = os.environ["DATABASE_URL"].replace("+asyncpg", "")` (psycopg2 is installed for this).
- `versions\0001_initial_schema.py`: the upgrade runs `op.execute()` blocks containing, in this order:
  1. The two extensions and four enum types from SPEC 8.2 verbatim.
  2. The `embedding_config` table from SPEC 8.1, but REMOVE the line `CONSTRAINT one_active_config UNIQUE (is_active)`.
  3. All remaining tables from SPEC 8.2 verbatim, with one change: in `knowledge_documents`, add two columns after `processed`:
     `indexed_at TIMESTAMP WITH TIME ZONE,` and `content_sha256 VARCHAR(64),`
  4. `CREATE UNIQUE INDEX one_active_embedding_config ON embedding_config (is_active) WHERE is_active = TRUE;`
  5. `INSERT INTO embedding_config (provider, model_name, dimensions, is_active) VALUES ('openai', 'text-embedding-3-small', 1536, TRUE);`
  6. All indexes from SPEC 8.3 verbatim (B-tree, GIN, both HNSW indexes).
  7. The trigger function and both triggers from SPEC 8.4 verbatim.
- Downgrade may simply drop the schema objects in reverse or raise NotImplementedError; this is a single-user project.

### Step 10: main.py and health router

- `main.py`: create FastAPI app, add the request-ID middleware, CORS middleware with `allow_origins=[settings.CORS_ALLOWED_ORIGIN]` and `allow_credentials=True` (never `*`), include health router and metrics route.
- `routers\health.py`:
  - `GET /health/live`: return `{"status": "alive"}` unconditionally.
  - `GET /health/ready`: check Postgres (`SELECT 1`), Redis (`PING`), and report which LLM provider keys are configured. Response shape per SPEC 17.1. Return 503 if Postgres or Redis fail. LLM check at this stage only reports `"configured"` or `"missing_key"` per provider; real reachability arrives with PLAN-04.

### Step 11: celery_app.py

Minimal Celery app: `Celery("odin", broker=settings.REDIS_URL, backend=settings.REDIS_URL)`, `task_track_started=True`, empty `beat_schedule = {}` dict (PLAN-09 fills it). A single smoke task `ping` returning `"pong"`.

### Step 12: bring it up and migrate

Run each as its own command from the Odin root:

1. `docker compose -f docker-compose.dev.yml up -d --build`
2. `docker compose -f docker-compose.dev.yml exec gateway-api alembic upgrade head`

### Step 13: initial commit

1. `git add -A`
2. Check `git status` output: `.env`, `keys`, `workspace` must NOT be staged.
3. `git commit -m "ODIN foundation: dev stack, schema, observability"`

## Edge cases a weaker model would miss

1. **Do not use the plain `postgres` image.** It has no pgvector. Use `pgvector/pgvector:pg16`. The extension still needs `CREATE EXTENSION vector;` in the migration, and `uuid-ossp` needs its double quotes: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
2. **Alembic and asyncpg do not mix.** The app uses `postgresql+asyncpg://`; Alembic must strip `+asyncpg` and run through psycopg2. If you point Alembic at the asyncpg URL you get `MissingGreenlet` errors.
3. **embedding_config UNIQUE(is_active) is a spec bug.** A plain unique constraint on a boolean allows at most one TRUE and one FALSE row ever. Use the partial unique index from Step 9.4 instead. See PLAN-00 deltas.
4. **The enum types must exist before the tables** that reference them, and SQLAlchemy models must declare `create_type=False`, otherwise the app tries to re-create the types at runtime.
5. **HNSW index creation fails on an empty-dimension column.** The `embedding` columns are declared `VECTOR(1536)` with a fixed dimension; keep it fixed. Changing embedding models to a different dimension is a migration plus re-embed job, not a config flip (SPEC 8.1 stores the intent; the column stays typed).
6. **Windows bind mounts and permissions.** All Python runs inside Linux containers; never run alembic or celery directly on the Windows host. Host ports 5433/6380 are remapped on purpose; `psql` from Windows must use `-p 5433`.
7. **`depends_on` does not wait for Postgres readiness.** The migrate command in Step 12 runs after `up -d`; if it races the DB, wait two seconds and rerun the exec command. Do not add sleep loops to the app itself; `/health/ready` is the readiness signal.
8. **CORS with credentials cannot use wildcard origins.** `allow_origins=["*"]` with `allow_credentials=True` is rejected by browsers. Use the explicit origin from settings (SPEC 3.2).
9. **conversations and tasks get `updated_at` via DB triggers on UPDATE only.** Inserting a message does not touch the conversation row; PLAN-03 handles that in the service layer. Do not rely on the trigger for it.
10. **`.env` must never be committed.** Verify in Step 13.2. The compose file reads it via `env_file`, and `POSTGRES_*` interpolation reads it from the shell environment of compose itself; both work because compose auto-loads `.env` from the project root.

## Acceptance criteria (verify each)

1. `docker compose -f docker-compose.dev.yml ps` shows gateway-api, celery-worker, celery-beat, database-node, redis-broker all running.
2. `alembic upgrade head` completed. `docker compose -f docker-compose.dev.yml exec database-node psql -U odin -d odin -c "\dt"` lists 19 tables plus `alembic_version`.
3. The same psql with `-c "\di"` shows `one_active_embedding_config`, `idx_kb_vector_cosine`, `idx_memories_vector_cosine`, `idx_messages_content_gin`.
4. `curl http://localhost:8000/health/live` returns 200. `curl http://localhost:8000/health/ready` returns 200 with the checks JSON.
5. `curl http://localhost:8000/metrics` returns Prometheus text containing `http_requests_total`.
6. `docker compose -f docker-compose.dev.yml logs gateway-api --tail 5` shows single-line JSON log entries containing a `request_id` field.
7. `git log --oneline` shows the initial commit; `git status` shows `.env` untracked-ignored.
