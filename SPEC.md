# ODIN: Omniscient Digital Intelligence Network

## Software Requirements Specification (SRS)

- **Version:** 2.0
- **Author:** Ali Moyo
- **Date:** 2026-07-10
- **Status:** Approved / Production-Ready

---

## Document 01: Vision & Product Definition

### 1.1 Project Name

**ODIN** (Omniscient Digital Intelligence Network) is the secure personal orchestration ecosystem. **Hermes** is the cognitive AI assistant core operating natively within ODIN.

The name draws from Norse mythology: Odin, the Allfather, sacrificed his eye at Mimir's well to gain omniscience. His two ravens, Huginn (thought) and Muninn (memory), fly across the world each day and report back everything they observe. In this system, the WhatsApp gateway, web dashboards, terminal clients, and file watchers are the ravens. Hermes sits at the centre, always watching, always knowing.

### 1.2 Vision Statement

ODIN is a secure, personal AI-powered operating environment designed to enable a single power user to manage software development, compliance documentation, learning syllabi, cloud infrastructure, finances, and day-to-day productivity workflows through a singular intelligent assistant.

Unlike traditional isolated wrappers, ODIN decouples presentation layers from the core execution engine. Every interface, whether a responsive single-page web dashboard, WhatsApp webhook, terminal client, or future mobile app, interacts with an identical, synchronized AI engine, long-term memory framework, central task queue, and specialized vector knowledge base.

### 1.3 Mission

Eliminate cognitive context switching. Instead of manually jumping across VS Code, Git branches, WhatsApp windows, calendar interfaces, markdown notes, Cloudflare dashboard grids, Docker consoles, SSH terminal buffers, and file explorers, the user executes their operational life from ODIN. All downstream systems are orchestrated programmatically behind the scenes.

### 1.4 Product Philosophy

ODIN is not a chatbot, an IDE extension, or an administrative project tracker. It is the intelligent orchestration layer running above all of them: a cohesive operating environment for the user's digital workspace.

### 1.5 Core Principles

**One Brain:** There is only one AI. Whether instructions arrive via WhatsApp voice notes, web dashboards, CLI triggers, or API webhooks, Hermes evaluates context using the same shared memories, historic conversational threads, and tool execution engines.

**Many Interfaces:** Interface fabrics are interchangeable. Work can be initialized via WhatsApp commands on the go, monitored dynamically via WebSockets on the Web Dashboard, and completed via terminal tools.

**Project-Centric Structure:** Every operational tracking asset belongs to a project. Projects contain references to file directories, database configurations, active tasks, Git repositories, system logs, and localized context parameters.

**Targeted Workspaces:** Projects are logically isolated into high-level life domains:

- **Development:** Software codebases (ThemisIQ), deployments, Docker clusters, repository checks.
- **Compliance:** Regulatory specs (GDPR, CCPA, ISO 27001/42001), RoPA documents, safety evaluations.
- **Learning:** Professional tracks (CISA, CIPP/E, MBA), technical reference notes, scheduled active-recall cards.
- **Finance:** Balance constraints, active VPS subscriptions, certification budgets, tracking metrics.
- **Personal:** Task priorities, fitness logs, dynamic notifications, and reminders.

**Security First:** Built with strict zero-trust principles. Every interaction is cryptographically verified, fully logged, auditable, and restricted by strict directory sandboxing boundaries.

**AI as an Assistant:** Hermes is a proactive assistant. Destructive modifications (file deletions, repository merges, cloud infrastructure adjustments) require manual verification or confirmation before committing.

### 1.6 Primary User

Designed to optimize the individual workspace of a single user: Ali Moyo. However, state managers, tables, and API architectures must not preclude future multi-user migrations.

### 1.7 Success Criteria

The system is successful when the user can:

1. Use a WhatsApp voice note to trigger a task.
2. Verify progress in real-time on the Web Dashboard console.
3. Access the generated output files safely from any device synchronized via Syncthing.
4. Transition interfaces seamlessly with full historical context and zero manual session restoration.
5. Receive a spoken (TTS) response to voice-note queries on WhatsApp.
6. Recover fully from a VPS failure using automated backups within 1 hour.

---

## Document 02: Functional Requirements

### 2.1 User Authentication (AUTH)

**AUTH-01:** The system shall present a clean secure login interface demanding a verified email and cryptographic password pair.

**AUTH-02:** The system shall implement asymmetric RS256 JWT authorization tokens. The short-lived access token shall expire in 15 minutes, while a secure 30-day refresh token is written to an httpOnly, secure, SameSite=Strict cookie.

**AUTH-03:** The system shall enforce Time-Based One-Time Password (TOTP) two-factor authentication (2FA) configured via standard authenticator app QR codes.

**AUTH-04:** Optional "Remember me" configurations shall dictate refresh token retention limits up to 30 days.

**AUTH-05:** The system shall implement an automated password reset workflow using secure email transmission links (SMTP-configured).

**AUTH-06:** Unauthenticated API calls to protected endpoints shall result in immediate redirects to the login route with an explicit 401 Unauthorized header.

**AUTH-07:** The system shall lock the account for 15 minutes after 5 consecutive failed TOTP attempts, logging the lockout event to the immutable audit log.

**AUTH-08:** The system shall enforce a Content Security Policy (CSP) header on all responses, restricting script sources to `'self'` and blocking inline scripts except where explicitly nonced.

### 2.2 Operational Dashboard (DASH)

**DASH-01:** The dashboard must present a greeting tailored to the system's time-of-day accompanied by live calendar date variables.

**DASH-02:** The system shall render a live editable list displaying 3 to 5 high-priority action items synced instantly with the relational database.

**DASH-03:** The system shall provide drag-and-drop handles for instant priority reordering.

**DASH-04:** The "Recent Files" widget must render the last 5 files added or updated within the synchronized directories, enabling instant click-to-download events.

**DASH-05:** The "Running Tasks" component must dynamically subscribe to active background workers via WebSockets, displaying progress as a visual percentage indicator.

**DASH-06:** The dashboard shall host a compact mini-chat bar. Submitting complex markdown commands there must transition the user seamlessly into the main conversational layout.

### 2.3 Contextual Chat System (CHAT)

**CHAT-01:** The chat interface must host a persistent sidebar grouping historical threads by active projects or custom date boundaries.

**CHAT-02:** User and assistant chat messages must render with absolute timestamps, clean Markdown support, and complete syntax highlighting for standard code languages.

**CHAT-03:** The chat panel must provide an expandable panel highlighting active context variables (current project, injected memories, active tasks).

**CHAT-04:** The interface must allow linking any conversation directly to a project. Linking dynamically overrides Hermes' active system prompt to focus on related workspace file trees and vector databases.

**CHAT-05:** Files uploaded within a chat thread must automatically save into the active project directory, inserting a localized reference link in the chat log.

**CHAT-06:** If Hermes triggers an asynchronous background script, execution telemetry must stream updates directly into the active chat interface.

**CHAT-07:** The system shall support full-text indexing and search filters over all conversation logs.

**CHAT-08:** For voice-initiated queries (WhatsApp voice notes), the system shall offer a text-to-speech (TTS) rendering of the response via the same channel, limited to answers under 300 words. Longer answers send a text summary plus a link to the full response on the dashboard.

### 2.4 Task and Project Management (TASK / PROJ)

**TASK-01:** Tasks must support creation from the web interface, conversational prompts, or remote WhatsApp webhooks.

**TASK-02:** Task models must strictly monitor title, description, priority (high, medium, low), due dates, parent project ID, and status (todo, in_progress, done, archived).

**TASK-03:** Each task must support nested checkable subtask lists.

**TASK-04:** The system must record a structural change log tracking every transition of status or priority.

**PROJ-01:** The system must track structural project models comprising a unique name, description, visual UI icon, and absolute local server directory path.

**PROJ-02:** Archiving a project must hide the record from standard UI directories while retaining all database tracking logs and filesystem contents intact on disk.

### 2.5 File System & Knowledge Base (FILE / KB)

**FILE-01:** The system must render a visual file browser representing the local /ODIN root directory synchronized over Syncthing.

**FILE-02:** The file explorer must support drag-and-drop file uploads, writing files directly into chosen directory structures.

**FILE-03:** File uploads must validate against an allowlist of extensions (pdf, docx, txt, md, html, csv, json, py, js, ts, yaml, yml, xml, png, jpg, jpeg). Files exceeding 50 MB must be rejected with a clear error message.

**KB-01:** Uploaded documents (PDF, DOCX, TXT, MD, HTML) must automatically trigger an asynchronous parsing job.

**KB-02:** The ingestion pipeline must extract raw text, execute recursive character chunking with configurable parameters (default: 1,000 token limit with 200 token overlap; code files: 500 tokens with 100 overlap; legal/regulatory: 1,500 tokens with 300 overlap), generate embeddings via the configured model, and index them in the database via pgvector.

**KB-03:** Users must be able to directly append rich markdown text notes or web links to index into the knowledge base.

**KB-04:** Modified files identified by Syncthing or the local filesystem watcher must trigger auto-reindexing of vector values.

**KB-05:** Semantic search results must pass through a cross-encoder reranking step before injection into the LLM prompt. The top 5 chunks after reranking are used; each chunk carries a citation reference (document name, page/section number) that Hermes must include in the response.

### 2.6 WhatsApp Communication Gateway (WA)

**WA-01:** The system shall integrate with Meta's official WhatsApp Cloud API webhooks.

**WA-02:** All inbound webhook payloads must be verified using HMAC-SHA256 signature checking against the Meta App Secret via the `X-Hub-Signature-256` header. Payloads with missing or invalid signatures must be rejected with HTTP 401. If the app secret is not configured, the endpoint must return HTTP 503 (fail closed, never fail open).

**WA-03:** Incoming messages from verified phone numbers must be matched to the user, creating or appending to unified conversation threads.

**WA-04:** Voice note attachments must pass through an automated transcription pipeline (OpenAI Whisper) before being processed by Hermes. Voice notes exceeding 5 minutes (approx 5 MB) must be rejected with a polite "message too long" reply.

**WA-05:** The background engine shall dispatch direct proactive WhatsApp updates for task completion events, long-running script outputs, or infrastructure warnings.

**WA-06:** Inbound messages must be deduplicated by Meta message ID using a bounded in-memory set (max 500 entries, FIFO eviction). Meta retries delivery on slow acks; without dedup, the user receives duplicate responses.

**WA-07:** The WhatsApp webhook endpoint must enforce per-user rate limiting (default: 10 messages per minute) independent of the global auth rate limit.

**WA-08:** For voice-note queries, the system shall generate a TTS audio response (via a configurable provider) and send it as a WhatsApp audio message when the text answer is under 300 words.

---

## Document 03: Non-Functional Requirements

### 3.1 Performance & User Experience

**Data Retrieval Latency:** Core dashboard queries and task lists must load inside 1.0 second under standard operating conditions.

**Inference Initialization:** Streaming chat response tokens must begin rendering in the UI within 500ms of prompt dispatch.

**File System Scanning:** Directory indexes containing up to 10,000 files must resolve and display within 2.0 seconds.

**Concurrency Boundary:** Engineered specifically to run as a single-user system. Up to 5 concurrent background Celery tasks can execute safely in parallel without UI performance bottlenecks.

### 3.2 Security Hardening & Isolation

**In-Transit Protection:** Mandatory TLS 1.3 encryption across all communication routes, dropping legacy or unsecure cipher suites.

**At-Rest Protection:** Third-party cloud credentials and service keys must use AES-256-GCM encryption before writing to disk, utilizing a master decryption key provided at runtime via environment variable.

**Access Boundary Checks:** Input parameter paths must validate against traversal patterns (e.g., `../`). Absolute file reads are strictly sandboxed within the verified /ODIN directory.

**Authentication Protection:** The authentication API restricts attempts to a maximum of 5 actions per minute per IP address.

**Content Security Policy:** All HTTP responses must include a CSP header restricting script sources to `'self'` with nonce-based exceptions for inline scripts required by the SPA. Frame-ancestors must be set to `'none'`.

**CORS Policy:** The API must enforce an explicit CORS allowlist containing only the dashboard origin (e.g., `https://odin.yourdomain.com`). Wildcard origins (`*`) are prohibited.

### 3.3 Reliability & Availability

**Monolithic Resilience:** Built as an isolated modular monolith, facilitating simple local virtual server deployments.

**LLM Provider Resilience:** The model router must implement a circuit breaker pattern: if the primary LLM provider returns 3 consecutive errors or exceeds a 30-second timeout, traffic automatically switches to the fallback provider. The circuit resets after 60 seconds. Supported fallback chain: Anthropic (primary) -> DeepSeek (secondary) -> Google Gemini (tertiary) -> OpenAI (quaternary) -> local Ollama instance (emergency).

**Integrations Resilience:** If external communication lines (such as Meta Cloud gateways) experience timeouts, core local services, files, and database indexes must remain operational.

**Backup & Recovery:** Automated `pg_dump` backups must run daily at 02:00 UTC, compressed and encrypted, with the latest 30 copies retained locally and the latest 7 synced offsite via rsync/rclone. Recovery from a full backup must be achievable within 1 hour. See Document 14 for the Celery Beat schedule entry.

### 3.4 Observability

**Structured Logging:** All application logs must be emitted as JSON lines with fields: `timestamp`, `level`, `service`, `request_id`, `user_id`, `message`, `duration_ms`. Logs are written to stdout for Docker log collection.

**Metrics Endpoint:** The application must expose a `/metrics` endpoint in Prometheus exposition format, reporting: request count by endpoint and status code, request latency histograms, active WebSocket connections, Celery queue depth, LLM call latency by provider, and pgvector query latency.

**Health Checks:** The application must expose:
- `GET /health/live` returning 200 if the process is running (liveness probe).
- `GET /health/ready` returning 200 only if PostgreSQL, Redis, and at least one LLM provider are reachable (readiness probe).

**Request Tracing:** Every inbound HTTP request must be assigned a unique `X-Request-ID` header (generated if not present), propagated through all internal service calls and logged in every log line for that request.

---

## Document 04: System Architecture

### 4.1 System Topography

ODIN separates client displays from core business logic using an asynchronous, event-driven modular architecture:

```
+------------------------------------------------------------------------+
|                          Nginx Reverse Proxy                           |
|             (TLS Termination, Static SPA Delivery, /metrics)           |
+-----------------------------------+------------------------------------+
                                    |
+-----------------------------------v------------------------------------+
|                         FastAPI Core Monolith                          |
|                                                                        |
|  +------------------+    +------------------+    +------------------+  |
|  |   Auth Service   |    |   Chat Service   |    |   Task Service   |  |
|  +------------------+    +------------------+    +------------------+  |
|  +------------------+    +------------------+    +------------------+  |
|  | Project Service  |    |   File Service   |    | Knowledge Base   |  |
|  +------------------+    +------------------+    +------------------+  |
|  +------------------+    +------------------+    +------------------+  |
|  | Memory Service   |    | Log/Activity Svc |    | Integration Svc  |  |
|  +------------------+    +------------------+    +------------------+  |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  |                  Hermes AI Execution Core                        |  |
|  |   - Intent Classification Engine & Context Assembler             |  |
|  |   - LLM Tool Calling Layer (Anthropic SDK, direct)               |  |
|  |   - Circuit Breaker & Provider Failover                          |  |
|  |   - Token Budget Manager & Manual Gate Enforcement               |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  |                 Celery Background Worker Cluster                  |  |
|  |   - Document Chunk Extraction & pgvector Pipeline                |  |
|  |   - Scheduled Cloud Infrastructure Sweeps (Cloudflare/Hetzner)   |  |
|  |   - Daily pg_dump Backup & Offsite Sync                          |  |
|  |   - Memory Consolidation & Conversation Summarization            |  |
|  +------------------------------------------------------------------+  |
+-----------------------------------+------------------------------------+
                                    |
        +---------------------------+---------------------------+
        |                                                       |
+-------v--------------------------+               +------------v-------+
|     PostgreSQL Vector Database   |               |     Redis Cache     |
|  (ACID Storage & pgvector Index) |               | (Celery & Pub/Sub) |
+----------------------------------+               +--------------------+
```

### 4.2 Core Interactions

The Web Panel queries FastAPI through robust REST pipelines while establishing persistent WebSocket channels to ingest real-time conversational streaming and task progress indicators.

Syncthing runs as an independent daemon. When folder synchronizations write changes to disk, the server watchdog detects these events via inotify hooks, dispatching an API webhook to queue re-indexing processes.

Hermes Core coordinates data fetching. When a message is processed, Hermes retrieves conversation logs from PostgreSQL, checks Redis context caches, extracts related text blocks using pgvector, formats LLM prompts, processes tool selections, and updates the task system accordingly.

### 4.3 LLM Provider Architecture

Hermes uses a direct integration with the Anthropic SDK (not LangChain) for maximum control and minimal dependency surface. The provider layer implements:

**Model Router:** A thin abstraction that accepts a provider config and dispatches to the appropriate SDK. Supported providers: Anthropic (primary), DeepSeek (secondary), Google Gemini (tertiary), OpenAI (quaternary), Ollama (local fallback). Each provider uses its native SDK for maximum compatibility.

**Circuit Breaker:** Per-provider health tracking. After 3 consecutive failures or timeouts exceeding 30 seconds, the circuit opens and traffic routes to the next provider in the chain. The circuit half-opens after 60 seconds to test recovery.

**Token Budget Manager:** Each conversation turn is allocated a maximum context window budget. The manager tracks: system prompt tokens, injected memory tokens, RAG chunk tokens, conversation history tokens, and reserves space for the response. If the total exceeds the model's context window, oldest conversation turns are pruned first, then RAG chunks are reduced from 5 to 3.

**Streaming:** All LLM calls use streaming by default. The streaming adapter normalizes provider-specific SSE formats into a unified token stream consumed by the WebSocket and WhatsApp response handlers.

```python
from anthropic import Anthropic

client = Anthropic()

def call_llm(messages: list, tools: list, system: str, max_tokens: int = 4096):
    """Direct Anthropic SDK call with streaming. No LangChain."""
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=tools,
        thinking={"type": "adaptive"},
    ) as stream:
        for event in stream:
            yield event
```

---

## Document 05: Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend UI | React 18, Vite, Tailwind CSS, React Query, Zustand, TipTap Editor | Delivers a high-density, responsive SPA with fast HMR dev cycles. Vite builds to static files served directly by nginx, no Node runtime needed in production. |
| Backend Core | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (Async), Alembic | Delivers high-performance, type-safe API routers with rich library bindings. |
| AI Orchestration | Anthropic SDK, DeepSeek API, Google Gemini SDK, OpenAI SDK, Ollama Interface, Custom Tool Schemas | Direct SDK integrations per provider avoid LangChain's abstraction overhead. Custom tool dispatcher gives full control over the ReAct execution loop. Model router handles failover across all five providers. |
| Database | PostgreSQL 15+ with pgvector Extension | Consolidates transactional application data and semantic vector embeddings inside a single database. |
| Messaging | Redis 7 & Celery | Drives background queues, task routing, caching layers, and WebSocket publish-subscribe systems. |
| File Mirroring | Syncthing Core Daemon | Secure, decentralized file synchronization across devices without third-party cloud dependencies. |
| Observability | Prometheus client, JSON structured logging | Lightweight metrics and tracing without external SaaS dependencies. |
| Deployments | Docker Engine & Multi-stage Compose | Guarantees clean system isolation and identical environments across dev and production. |

---

## Document 06: Backend Services

### 6.1 Authentication Module (/auth)

Responsible for JWT token generation, cookie-based session persistence, TOTP cryptosystem verifications, and master identity validation. It encrypts user secrets and handles secure, restricted paths. Enforces account lockout after 5 failed TOTP attempts (AUTH-07).

### 6.2 Conversational Stream Module (/chat)

Coordinates chat logging and historical retrievals. Manages WebSockets via `/ws/chat/{conversation_id}` to stream LLM generation tokens back to the user interface in real-time.

**WebSocket Authentication:** WebSocket connections use a short-lived ticket pattern rather than JWT in query parameters (which leak in server logs). The client first calls `POST /api/v1/ws-ticket` with a valid access token, receiving a single-use ticket (UUID, valid for 30 seconds). The client then connects to `/ws/chat/{conversation_id}?ticket={ticket_uuid}`. The server validates and immediately invalidates the ticket on first use.

### 6.3 Task Lifecycle Module (/tasks)

Enforces strict transactional CRUD operations for tasks and checklists. Publishes task state changes directly to Redis to notify connected WebSocket clients.

### 6.4 Filesystem Mapping Module (/files)

Enforces canonical workspace reads and writes. Prevents path-traversal attacks. Provides secure, chunked streaming file download and upload routes. Validates file extensions and sizes against the allowlist (FILE-03).

### 6.5 Knowledge & Memory Module (/kb, /memory)

Drives text parsing, recursive sliding window chunking (with per-type configurable parameters), embedding generation via the configured provider, cross-encoder reranking, semantic searches with citation tracking, and user key-value memories.

### 6.6 System Integrations Module (/integrations)

Encapsulates developer configurations and OAuth loops (e.g., GitHub authorization). Provides a standard Python interface for Hermes to interact with downstream systems.

### 6.7 Health & Observability Module (/health, /metrics)

Exposes liveness and readiness probes (3.4) and a Prometheus-compatible metrics endpoint. The readiness probe checks PostgreSQL connectivity, Redis connectivity, and at least one LLM provider reachability.

---

## Document 07: Frontend Specification

### 7.1 Web Layout Real Estate Schema

The interface is designed for high information density, prioritizing situational awareness over empty space.

```
+-----------------------------------------------------------------------------------+
|  ODIN NAVIGATION BAR  | Focus Workspace: [Development/ThemisIQ]  | Sync Status: OK |
+------------------------+----------------------------------+-----------------------+
|                        |                                  |                       |
|  WORKSPACE TREE        |          CENTRAL CHAT INTERFACE  | SYSTEM METRIC PANEL   |
|                        |                                  |                       |
|  [-] /ODIN             |  [14:15] Ali: Refactor backend   | Running Tasks:        |
|    [+] /Inbox          |          auth middleware.        | -> Auth Refactor (85%)|
|    [-] /Projects       |                                  |                       |
|      [-] /ThemisIQ     |  [14:16] Hermes: Investigating   | Proactive System Log: |
|        > src/auth.py   |          file structures.        | [14:00] WAF Blocked 12|
|        > tests/        |  [14:17] Hermes: Awaiting system | [13:12] Hetzner OK    |
|    [+] /Knowledge      |          approval for code patch |                       |
|    [+] /Learning       |                                  | Active Budgets:       |
|    [+] /Outputs        |  +----------------------------+  | Certs: $450/$1200     |
|                        |  |   [APPROVE PATCH BUTTON]   |  |                       |
|                        |  +----------------------------+  | Quiz Status:          |
|                        |                                  | CISA Domain 3: 88%    |
+------------------------+----------------------------------+-----------------------+
| LIVE PROCESS CONSOLE: ~$ docker exec -it themisiq-backend pytest tests/           |
+-----------------------------------------------------------------------------------+
```

### 7.2 UI Routing Core

- `/login` - Credential collection and TOTP validation.
- `/` - Master operational overview (priorities, tasks, recent files, activity logs).
- `/chat` - Conversational panels with sidebar navigation and context settings.
- `/tasks` - In-depth checklist view with status filters and task histories.
- `/files` - Structural explorer mapping the synchronized workspace tree.
- `/knowledge` - PDF/Doc upload platform and semantic verification tests.

### 7.3 Frontend State Management

The frontend utilizes a split state management strategy:

**Zustand** stores handle local client-side states (active UI panels, socket states, active project toggles).

**React Query** manages server state queries, implementing invalidation hooks on mutations to keep local views perfectly synchronized with the PostgreSQL database.

### 7.4 Build & Deployment

The frontend is built with **Vite** as a static SPA bundle. The production build outputs to a `dist/` folder containing only HTML, CSS, and JS files. Nginx serves these static files directly with aggressive caching headers (`Cache-Control: public, max-age=31536000, immutable` for hashed assets). No Node.js runtime is needed in production.

---

## Document 08: Database Design

### 8.1 Embedding Configuration

The system supports configurable embedding dimensions to avoid lock-in to a single provider. The active embedding model and its dimension are stored in a configuration table. Changing the model triggers a background re-embedding job for all existing chunks.

```sql
CREATE TABLE embedding_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL DEFAULT 'openai',
    model_name VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    dimensions INTEGER NOT NULL DEFAULT 1536,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT one_active_config UNIQUE (is_active) -- only one active config
);
```

### 8.2 Database Schema (Production-Grade DDL)

The database structure consolidates primary operational tracking, conversational timelines, system task lifecycles, and vector knowledge structures:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Enumerated State Profiles
CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done', 'archived');
CREATE TYPE task_priority AS ENUM ('high', 'medium', 'low');
CREATE TYPE chat_role AS ENUM ('user', 'assistant', 'system');
CREATE TYPE interface_origin AS ENUM ('web', 'whatsapp', 'terminal', 'system');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(512),
    timezone VARCHAR(50) DEFAULT 'UTC',
    two_factor_secret VARCHAR(255),
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    totp_failed_attempts INTEGER DEFAULT 0,
    totp_locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ws_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    workspace_path VARCHAR(512) NOT NULL,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status task_status DEFAULT 'todo',
    priority task_priority DEFAULT 'medium',
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subtasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE task_changelog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    title VARCHAR(255) DEFAULT 'New Conversation',
    is_archived BOOLEAN DEFAULT FALSE,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role chat_role NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'upload', 'note', 'link'
    chunk_config JSONB DEFAULT '{"chunk_size": 1000, "overlap": 200}'::jsonb,
    processed BOOLEAN DEFAULT FALSE,
    embedding_config_id UUID REFERENCES embedding_config(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    section_ref VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(255),
    value TEXT NOT NULL,
    embedding VECTOR(1536),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    source interface_origin NOT NULL,
    description TEXT NOT NULL,
    related_entity_type VARCHAR(100),
    related_entity_id UUID,
    request_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE integration_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service VARCHAR(50) NOT NULL, -- 'github', 'cloudflare', 'whatsapp', etc.
    credentials BYTEA NOT NULL, -- AES-256-GCM encrypted credentials block
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_service UNIQUE(user_id, service)
);

CREATE TABLE tool_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    pattern TEXT NOT NULL,
    auto_approve BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_tool_pattern UNIQUE(user_id, tool_name, project_id, pattern)
);

CREATE TABLE llm_provider_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL,
    consecutive_failures INTEGER DEFAULT 0,
    circuit_open BOOLEAN DEFAULT FALSE,
    circuit_opened_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    last_failure_at TIMESTAMP WITH TIME ZONE,
    total_calls BIGINT DEFAULT 0,
    total_failures BIGINT DEFAULT 0,
    avg_latency_ms REAL
);

CREATE TABLE backups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    size_bytes BIGINT NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    offsite_synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 8.3 Strategic Indexes

**B-Tree Indices:** Created for all foreign keys, query statuses, and target filters:

```sql
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_activity_log_created ON activity_log(created_at);
CREATE INDEX idx_activity_log_user_type ON activity_log(user_id, event_type);
CREATE INDEX idx_ws_tickets_expires ON ws_tickets(expires_at) WHERE used = FALSE;
CREATE INDEX idx_conversations_updated ON conversations(user_id, updated_at);
```

**Full-Text Search Indices (GIN):** Optimized for broad chat log queries:

```sql
CREATE INDEX idx_messages_content_gin ON messages
    USING gin(to_tsvector('english', content));
```

**Vector Cosine Similarity Indices (HNSW):** Essential to accelerate semantic context fetches. HNSW is preferred over IVFFlat for better recall at low dataset sizes:

```sql
CREATE INDEX idx_kb_vector_cosine ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_memories_vector_cosine ON memories
    USING hnsw (embedding vector_cosine_ops);
```

### 8.4 Automatic Timestamp Updates

```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tasks_updated
    BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_conversations_updated
    BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## Document 09: AI Agent Framework (Hermes Core)

### 9.1 Core Ingestion & ReAct Execution Loop

Hermes evaluates incoming user instructions using a deterministic, state-bounded execution loop:

```
[IDLE] -> Receives Input -> [PLANNING] (Gathers Context, Decides Actions)
                                |
                                v
[IDLE] <- Sends Response <- [EXECUTING] (Runs Tool Calls & Verifications)
```

**Context Assembly:** Hermes loads short-term message buffers, scans system directories, queries semantic memory variables, and pulls related knowledge chunks from pgvector. The Token Budget Manager (4.3) ensures the assembled context fits within the model's context window.

**Intent Classification:** Hermes processes user intent using a structured classification system:

- `chat`: Conversational exchanges and programmatic queries.
- `task_crud`: Operations modifying task attributes, checklist items, or schedules.
- `file_operation`: Secure filesystem creations or canonical checks.
- `knowledge_query`: Local vector database searches to synthesize answers.
- `integration_action`: Secure operations calling Git, Hetzner, or Cloudflare APIs.

**Execution Planning:** Hermes compiles a linear action queue. The system maps tools (e.g., `create_file()`) directly to secure Python handlers wrapped with Pydantic type specifications. Tool definitions use the Anthropic SDK's native tool format:

```python
tools = [
    {
        "name": "create_task",
        "description": "Create a new task in the specified project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "project_id": {"type": "string", "format": "uuid"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "due_date": {"type": "string", "format": "date-time"}
            },
            "required": ["title"]
        }
    }
]
```

**Safety Intercepts:** Destructive actions (e.g., code merges, server configurations, file deletions) prompt the execution loop to pause, transition the state machine to `GATE_LOCKED`, and dispatch an authorization token to the active user interface. Execution resumes only upon cryptographic token validation.

**Tool Approval Persistence:** When a user approves a tool invocation, the system records the tool name, project context, and parameter pattern in the `tool_approvals` table. Future invocations matching an approved pattern skip the gate automatically. Approvals are scoped to a specific project and can be revoked from the dashboard settings.

### 9.2 Structured Output Validation

All tool call results pass through Pydantic model validation before being returned to Hermes. If a tool returns data that fails validation, Hermes receives a structured error (not a raw exception) and can retry or report the failure cleanly to the user.

---

## Document 10: Memory System

### 10.1 Structured Memory Architecture

**Episodic Memory (Short-Term Working Context):** Live Redis caches storing the immediate chat turn buffers (max 30 threads) to keep interface updates highly responsive.

**Semantic Memory (Relational Metadata Store):** Relational PostgreSQL records capturing user characteristics, system settings, and explicit facts (e.g., "Database port is 5432").

**Procedural Memory (Procedural Patterns):** Stored key-value parameters representing configuration settings and workflow routines (e.g., git branching patterns, build scripts).

### 10.2 Processing Lifecycle

**Explicit Storage Actions:** Triggered immediately when the user prefaces instructions with "Remember that...". The system generates a vector representation of the statement and persists it to the memories database table.

**Implicit Background Extraction:** A post-conversation hook parses completed chat histories to extract recurring entities and preferences. Hermes then surfaces these implicit extractions as memory suggestions on the dashboard for user validation. The user must confirm before implicit memories are persisted (never auto-commit inferred facts).

**Context Retrieval Loops:** When a prompt is submitted, Hermes executes a quick vector cosine similarity lookup across the user's memory space, prepending the top matching results directly into the LLM system prompt.

### 10.3 Memory Lifecycle Management

**Access Tracking:** Each memory records `access_count` and `last_accessed_at`. Memories that have not been accessed in 90 days are surfaced in a monthly "memory review" dashboard widget for the user to confirm or archive.

**Conflict Resolution:** When an implicit extraction contradicts an existing explicit memory, the system always preserves the explicit memory and flags the conflict for manual resolution rather than silently overwriting.

**Capacity Limits:** The memory store enforces a soft limit of 1,000 active memories per user. Beyond this threshold, the monthly consolidation job (see Document 14) surfaces the least-accessed memories for archival review.

### 10.4 Conversation Summarization

When a conversation exceeds 50 messages, a background Celery task generates a summary (stored in `conversations.summary`). When the conversation is later loaded for context injection, the summary replaces the full message history to conserve token budget, with the most recent 10 messages appended verbatim.

---

## Document 11: Workspace Management

### 11.1 Directory Tree Topography

The system monitors and controls files inside a synchronized local directory hierarchy:

```
/home/ali/ODIN/
  Inbox/             # Ingress bucket for files uploaded via chat or WhatsApp webhooks
  Projects/          # Active workspace directories
    ThemisIQ/        # Compliance workspace directory
    BaseEngine/      # Engineering workspace directory
  Knowledge/         # Policy standards, regulatory guidelines, academic notes
  Learning/          # Markdown notes, lecture outlines, study records
  Outputs/           # Completed AI exports, documentation packages, and templates
```

### 11.2 Watchdog Filesystem Watcher Pipeline

The backend runs a background process utilizing the Linux kernel's file watcher system (inotify) to track modifications inside the active workspace and index documents automatically:

```python
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class WorkspaceWatcherHandler(FileSystemEventHandler):
    def __init__(self, indexing_callback):
        self.indexing_callback = indexing_callback
        self.sandbox_path = "/home/ali/ODIN/"

    def on_modified(self, event):
        if not event.is_directory:
            canonical_path = os.path.realpath(event.src_path)
            if canonical_path.startswith(self.sandbox_path):
                self.indexing_callback(canonical_path)
            else:
                logger.warning(
                    "Blocked out-of-bounds modification attempt",
                    extra={"path": canonical_path}
                )
```

### 11.3 Syncthing Conflict Handling

When Syncthing detects a file conflict (producing `.sync-conflict-*` files), the watchdog handler must:

1. Log the conflict to the activity log with both file versions.
2. Surface a notification to the dashboard: "File conflict detected: {filename}. Review in the file browser."
3. Do NOT auto-index the conflict file. Wait for user resolution.

---

## Document 12: Integrations

### 12.1 WhatsApp Cloud API Webhook Core

**Inbound Route Hook:** Exposes an HTTPS POST interface at `/api/v1/integrations/whatsapp/webhook` to capture incoming payloads.

**Signature Verification:** Every inbound POST must be verified using the `X-Hub-Signature-256` header against the Meta App Secret (WA-02). The raw request body bytes are used for HMAC computation (never re-serialized JSON). Verification failure returns 401. Missing app secret configuration returns 503.

**Message Deduplication:** Inbound messages are tracked by Meta message ID (`wamid.*`) in a bounded in-memory set (WA-06). Duplicate deliveries (caused by Meta's retry policy on slow acks) are silently acknowledged with 200 without processing.

**Audio Transcription Pipeline:** Binary voice notes are intercepted, converted to .mp3 using ffmpeg utilities, and processed through OpenAI's Whisper API before being routed to Hermes for intent classification. Voice notes exceeding 5 minutes are rejected (WA-04).

**Text-to-Speech Responses:** For voice-initiated queries, short answers (under 300 words) are rendered to audio via a TTS provider and sent back as WhatsApp audio messages (WA-08).

**State Notifications:** Long-running execution queues leverage this channel to dispatch proactive status notifications directly to your phone.

### 12.2 GitHub Ecosystem Bridge

Implements the standard OAuth2 loop to establish secure, tokenized API authentication channels. Hermes is authorized to fetch active issues, generate standard code-diff branches, and draft pull requests, using user confirmations for writes.

### 12.3 Cloudflare Network Management API

Uses secure API bearer tokens to pull firewall event streams and check SSL expiration dates. Hermes reports domain status and logs directly within your chat thread.

### 12.4 Hetzner Compute API Bridge

Queries server metrics (CPU load, bandwidth consumption, backup history) via the cloud REST interface. Proactively registers alerts if monitoring checks encounter failures or missing automated backup structures.

---

## Document 13: Security Model

### 13.1 Session Validation

**Access Tokens:** Evaluated in-memory via short-lived JWT signatures (RS256, 15-minute expiry).

**Refresh Tokens:** Hashed (SHA-256) and stored in the `sessions` table. The raw token is written to a secure, httpOnly, SameSite=Strict cookie. Because `SameSite=Strict` prevents the cookie from being sent on cross-origin requests, traditional CSRF attacks are already mitigated. No separate CSRF token mechanism is needed.

**Ownership Verification Constraints:** Because the application is a single-user system, the API router enforces a strict validation rule: any requested database entity ID must explicitly match the authenticated user's ID.

**WebSocket Security:** WebSocket connections are authenticated via the short-lived ticket pattern described in Document 06.2, preventing JWT leakage in server access logs.

### 13.2 Transit & At-Rest Cryptography

**In-Transit Encryption:** Enforced globally using TLS 1.3, automatically rejecting weak, outdated cipher suites.

**Credential Protection:** High-security variables (OAuth tokens, third-party API keys) are encrypted before database serialization using authenticated AES-256-GCM algorithms. Decryption keys are loaded into RAM strictly at runtime via environment variables. Encrypted credentials must never appear in plaintext in configuration files, Docker Compose manifests, or version control.

**Content Security Policy:** All responses include a CSP header: `default-src 'self'; script-src 'self' 'nonce-{random}'; style-src 'self' 'unsafe-inline'; connect-src 'self' wss://{domain}; frame-ancestors 'none'`.

### 13.3 Immutable Security Audit Log

All critical system events (authentication actions, token generation attempts, tool invocations, API credentials updates, TOTP lockouts, gate approvals) are committed to an append-only transaction history log. This data store is protected against manual user modification, ensuring clear historical audit records. Each log entry includes the `request_id` for correlation with application logs.

---

## Document 14: Automation Engine

### 14.1 Background Task Processing Queue (Celery Worker)

Resource-intensive computational steps are decoupled from primary HTTP request threads using Celery and Redis worker pools. The worker engine processes:

- Dynamic indexing of PDFs, DOCX, and text document uploads.
- Vector generation calculations.
- Deep codebase parsing and structural repository checks.
- Conversation summarization (triggered when a conversation exceeds 50 messages).
- Cross-encoder reranking for knowledge base queries.
- Database backup and offsite sync.

### 14.2 Scheduled Operational Routines (Celery Beat)

| Time | Frequency | Job | Description |
|---|---|---|---|
| 02:00 UTC | Daily | `backup_database` | Run `pg_dump`, compress with gzip, compute SHA-256 checksum, store locally. Sync latest 7 to offsite via rclone. Prune local copies older than 30 days. Record in `backups` table. |
| 08:00 UTC | Daily | `morning_agenda` | Compile top priority tasks and send a structured workspace overview to WhatsApp. |
| 01:00 UTC | Monday | `infra_audit` | Poll Hetzner and Cloudflare endpoints to check server workload metrics and SSL cert expirations. Flag warnings on the dashboard. |
| 03:00 UTC | Daily | `stale_task_cleanup` | Tasks with status `done` for over 14 days are auto-archived. Tasks with status `in_progress` and no update in 7 days trigger a dashboard notification. |
| 04:00 UTC | Sunday | `memory_consolidation` | Scan memories with `access_count = 0` and `created_at > 90 days ago`. Surface them in the dashboard review widget. Summarize groups of related low-access memories into single consolidated entries (pending user approval). |
| 04:30 UTC | Sunday | `conversation_summarize` | Find conversations with 50+ unsummarized messages. Generate and store summaries. |
| 05:00 UTC | Daily | `knowledge_reindex` | Check for documents whose source files have been modified since last indexing (via Syncthing timestamps). Re-chunk and re-embed changed documents. |
| 06:00 UTC | 1st of month | `ssl_cert_countdown` | Check all monitored domains' SSL expiration dates. If any expire within 30 days, create a high-priority task and send a WhatsApp alert. |
| 23:00 UTC | Daily | `ws_ticket_cleanup` | Delete expired and used WebSocket tickets older than 1 hour. |

---

## Document 15: Knowledge Base

### 15.1 Ingestion and Parsing Pipeline

```
Document Upload -> PDF/Text Extract -> Overlapping Token Chunking -> Embedding Model -> pgvector Index
```

**Extraction:** Intercepts uploaded binary formats, converting them to plain text streams (using pdfplumber or python-docx utilities). File type and size validation occurs before extraction (FILE-03).

**Configurable Chunking:** Splits extracted text strings into document blocks with parameters stored per document in `knowledge_documents.chunk_config`:

| Document Type | Chunk Size | Overlap | Rationale |
|---|---|---|---|
| General text (default) | 1,000 tokens | 200 tokens | Balanced context preservation |
| Source code (py, js, ts) | 500 tokens | 100 tokens | Shorter for precise function-level retrieval |
| Legal/regulatory (pdf) | 1,500 tokens | 300 tokens | Longer to preserve clause context |

**Embeddings Generation:** Batches chunks through the active embedding model (configured in `embedding_config` table) to generate vector arrays. Default: OpenAI `text-embedding-3-small` (1,536 dimensions).

**Vector DB Ingestion:** Commits chunks and vectors to the `knowledge_chunks` table with `chunk_index`, `page_number`, and `section_ref` for citation tracking. Updates the document's tracking status to processed.

### 15.2 Retrieval Augmented Generation (RAG) Flow

1. Incoming user questions trigger the `search_knowledge()` tool, which converts the query string into a search vector using the same embedding model.
2. The system performs a cosine similarity lookup against the HNSW index to retrieve the top 10 candidate document chunks.
3. Candidates pass through a cross-encoder reranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) to score relevance more precisely. The top 5 chunks after reranking are selected.
4. These text segments are injected directly into the LLM system prompt as verified context, with citation markers: `[Source: {filename}, p.{page_number}]`.
5. Hermes must include these citations in the response, enabling the user to verify claims against the original document in the file browser.

---

## Document 16: Deployment Architecture

### 16.1 Local Docker Compose Development Stack

The development stack runs inside a localized Docker network, utilizing persistent storage folders to enable rapid, hot-reloaded development cycles:

```yaml
version: '3.8'

services:
  gateway-api:
    image: odin-gateway:dev
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - /home/ali/ODIN:/home/ali/ODIN
    env_file:
      - .env
    depends_on:
      - database-node
      - redis-broker

  celery-worker:
    image: odin-worker:dev
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A core_worker.celery worker --loglevel=info
    volumes:
      - ./backend:/app
      - /home/ali/ODIN:/home/ali/ODIN
    env_file:
      - .env
    depends_on:
      - redis-broker

  celery-beat:
    image: odin-worker:dev
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A core_worker.celery beat --loglevel=info
    volumes:
      - ./backend:/app
    env_file:
      - .env
    depends_on:
      - redis-broker

  database-node:
    image: pgvector/pgvector:15-pgdg
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - local_db_data:/var/lib/postgresql/data

  redis-broker:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  local_db_data:
    driver: local
```

Note: all credentials are loaded from the `.env` file via `env_file:` directives. No secrets appear in this manifest. The `.env` file must never be committed to version control.

### 16.2 Production Server Deployment (Hetzner VPS Node)

Production systems run on a single Ubuntu Virtual Private Server secured with a strict firewall profile (UFW) and automated SSL termination:

**Nginx Reverse Proxy Gateway:** Terminated on the host system to intercept public traffic, handle automated certificate renewals via Cloudflare origin certificates, proxy secure WebSocket connections directly to the application container, and serve the static Vite SPA bundle.

**Production Container Isolation:** Runs isolated container environments with production configurations, keeping persistent database files secured inside encrypted volume containers.

**Backup Verification:** The daily backup job (14.2) writes to a local directory and syncs offsite. Monthly, a manual or automated restore test should verify backup integrity against a scratch database.

### 16.3 Production .env Template

```bash
# ODIN Production Configuration
# Copy this file to .env and fill in real values.
# NEVER commit the filled .env to version control.

# Core Application Security Keys
SECRET_KEY=REPLACE_WITH_64_CHAR_HEX
ENCRYPTION_KEY=REPLACE_WITH_BASE64_AES_KEY

# Database & Cache Connection Targets
DATABASE_URL=postgresql+asyncpg://REPLACE_USER:REPLACE_PASS@database-node:5432/odin_prod
DB_USER=REPLACE_USER
DB_PASSWORD=REPLACE_PASS
DB_NAME=odin_prod
REDIS_URL=redis://redis-broker:6379/0

# LLM Providers (chain: Anthropic -> DeepSeek -> Gemini -> OpenAI -> Ollama)
ANTHROPIC_API_KEY=REPLACE_WITH_KEY
DEEPSEEK_API_KEY=REPLACE_WITH_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com
GEMINI_API_KEY=REPLACE_WITH_KEY
OPENAI_API_KEY=REPLACE_WITH_KEY
OLLAMA_BASE_URL=http://localhost:11434

# Embedding Model
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# WhatsApp Cloud API
WHATSAPP_APP_SECRET=REPLACE_WITH_META_APP_SECRET
WHATSAPP_TOKEN=REPLACE_WITH_META_TOKEN
WHATSAPP_PHONE_NUMBER_ID=REPLACE_WITH_ID
WHATSAPP_VERIFY_TOKEN=REPLACE_WITH_RANDOM_STRING

# GitHub OAuth
GITHUB_CLIENT_ID=REPLACE_WITH_ID
GITHUB_CLIENT_SECRET=REPLACE_WITH_SECRET

# Infrastructure APIs
CLOUDFLARE_API_TOKEN=REPLACE_WITH_TOKEN
HETZNER_API_TOKEN=REPLACE_WITH_TOKEN

# Backup
BACKUP_LOCAL_DIR=/var/backups/odin
BACKUP_OFFSITE_REMOTE=REPLACE_WITH_RCLONE_REMOTE
BACKUP_RETENTION_DAYS=30

# CORS
CORS_ALLOWED_ORIGIN=https://odin.yourdomain.com
```

---

## Document 17: API Specification Reference

### 17.1 Core API Contracts

**POST /api/v1/chat/message**

Submits a conversational turn, triggering the active ReAct agent loop:

Request Schema (application/json):
```json
{
  "conversation_id": "8f3b29c1-421d-4e92-91a0-32df9c91b10a",
  "content": "Analyze the latest AI Governance framework in my Inbox directory.",
  "interface_origin": "web"
}
```

Response Schema (application/json):
```json
{
  "message_id": "b3e94411-cf12-421c-a988-dcf2b9a765d1",
  "status": "queued_for_generation",
  "metadata": {
    "active_project": "ThemisIQ",
    "injected_memory_count": 3,
    "token_budget": {
      "system": 850,
      "memories": 420,
      "rag_chunks": 2100,
      "history": 3200,
      "reserved_response": 4096,
      "total": 10666,
      "model_limit": 200000
    }
  }
}
```

**GET /api/v1/tasks**

Retrieves active tasks filtered by project and priority parameters:

Request Parameters:
- `project_id` (Query, Optional UUID)
- `status` (Query, Optional String)

Response Schema (application/json):
```json
[
  {
    "id": "27fa988b-11d2-4322-921a-e6cbfa3f99aa",
    "title": "Review AI Governance audit documentation",
    "status": "in_progress",
    "priority": "high",
    "due_date": "2026-07-15T18:00:00Z",
    "subtasks": [
      { "id": "1a2b", "title": "Extract RoPA values", "completed": true }
    ]
  }
]
```

**POST /api/v1/integrations/whatsapp/webhook**

Meta Cloud interface entrypoint processing remote commands. Requires valid `X-Hub-Signature-256` header.

Request Schema (application/json):
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "109283746501928",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": { "display_phone_number": "15550199999" },
            "messages": [
              {
                "from": "26377XXXXXXX",
                "id": "wamid.HBgL...",
                "timestamp": "1773000000",
                "text": { "body": "What are my tasks for today?" },
                "type": "text"
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

Response Schema (application/json):
```json
{
  "status": "delivered_to_queue",
  "event_id": "wamid.HBgL..."
}
```

**POST /api/v1/ws-ticket**

Generates a single-use WebSocket authentication ticket.

Response Schema (application/json):
```json
{
  "ticket": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "expires_in_seconds": 30
}
```

**GET /health/ready**

Readiness probe for load balancers and monitoring.

Response Schema (application/json):
```json
{
  "status": "healthy",
  "checks": {
    "postgresql": "ok",
    "redis": "ok",
    "llm_provider": "anthropic",
    "llm_status": "ok"
  }
}
```

---

## Document 18: Development Roadmap

```
Phase 1: Foundation (Weeks 1-12)
  -> Phase 2: Intelligence (Weeks 13-18)
    -> Phase 3: Extensions (Ongoing)
```

### 18.1 Phase 1: Foundation Infrastructure (Weeks 1-12)

1. Establish monorepo, multi-stage Docker configurations, and base database migration schemas using Alembic.
2. Construct the core authentication controllers, including TOTP 2FA setup hooks and account lockout.
3. Deliver the Web Dashboard priorities widget, filesystem viewer, activity feed, and streaming chat logs (Vite + React SPA).
4. Link the WhatsApp Business webhook gateway with signature verification and message dedup to convert text payloads into conversational chat records.
5. Activate base vector indexing pipelines to support document uploads and semantic RAG searches.
6. Implement automated daily pg_dump backup and offsite sync pipeline.
7. Set up structured JSON logging and Prometheus /metrics endpoint.

### 18.2 Phase 2: System Intelligence & Proactivity (Weeks 13-18)

1. Configure post-conversation Celery workers to extract episodic memory facts and surface suggestions on the dashboard (with user confirmation gate).
2. Build background automation routines to poll Hetzner API status logs and Cloudflare certificate expirations, raising priority alerts on failure.
3. Integrate voice note transcription capabilities within the WhatsApp Cloud API webhook using Whisper API channels.
4. Implement TTS response pipeline for voice-initiated queries.
5. Enable remote background script tracking, allowing users to initiate executions via WhatsApp and monitor progress on the dashboard.
6. Build the circuit breaker and provider failover chain (Anthropic -> DeepSeek -> Gemini -> OpenAI -> Ollama).

### 18.3 Phase 3: Production Refinement & UI Extensions (Ongoing)

1. Develop native tray-based client shells utilizing Electron or Tauri frameworks.
2. Design mobile notification utilities with React Native to provide rich operational alerts.
3. Implement custom visual drag-and-drop workflow designers, enabling users to orchestrate automation chains across services (e.g., "When a GitHub build fails, generate a task and notify me on WhatsApp").
4. Cross-encoder reranking integration for improved RAG accuracy.
5. Tool approval persistence UI in dashboard settings.

---

## Document 19: Coding Standards & Architectural Patterns

### 19.1 System Code Quality Rules

**Enforced Type-Hinting:** Every Python core module, endpoint router, and data model mapping must implement strict type annotations. Code integrations with missing types will trigger test suite deployment failures.

**Functional State Isolation:** Database modifications must execute within strict transactional blocks (`async with async_session()`), preventing memory leaks and state corruption issues.

**Unified Error Handling:** Critical operations must be wrapped within clear exception handles. Block exceptions must write detailed structured log entries (JSON format with request_id) to the PostgreSQL tracking log before failing gracefully.

**No Secrets in Code:** Configuration values, API keys, and credentials must only be loaded from environment variables or encrypted stores. Hardcoded secrets in source code, Docker manifests, or configuration templates trigger an immediate CI pipeline failure.

### 19.2 Standardized Business Component (Example)

```python
from typing import Any
from uuid import UUID
import structlog

logger = structlog.get_logger("odin.core")

async def execute_secure_system_transition(
    task_context: dict[str, Any],
    target_workspace_id: UUID,
) -> bool:
    """Executes a validated workspace state transition within the sandboxed container."""
    try:
        if not target_workspace_id:
            raise ValueError("Task context payload requires a valid target workspace ID.")

        # Secure business execution logic runs here...
        logger.info(
            "workspace_transition_completed",
            workspace_id=str(target_workspace_id),
        )
        return True
    except Exception:
        logger.exception(
            "workspace_transition_failed",
            workspace_id=str(target_workspace_id),
        )
        return False
```

---

## Document 20: Appendices

### 20.1 Terms and Definitions

| Term | Definition |
|---|---|
| ODIN | Omniscient Digital Intelligence Network: the unified personal operating environment. |
| Hermes Core | The cognitive AI execution engine processing instructions, orchestrating context, and executing tool calls. Named for the Greek messenger god who bridges all worlds. |
| Workspace Root | The local host folder path monitored by Syncthing and mapped directly to the backend filesystem service. |
| pgvector | An open-source vector similarity search extension for PostgreSQL, used to store and query high-dimensional embeddings. |
| Circuit Breaker | A resilience pattern that stops calling a failing service after consecutive errors, allowing it time to recover before retrying. |
| HNSW | Hierarchical Navigable Small World: an approximate nearest-neighbor index algorithm used by pgvector for fast vector similarity search. |
| ReAct | Reasoning + Acting: an agent execution pattern where the model alternates between reasoning about what to do and taking tool-call actions. |

### 20.2 Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-10 | Initial specification. |
| 2.0 | 2026-07-10 | Renamed AIOS to ODIN. Removed LangChain (replaced with direct Anthropic SDK). Replaced Next.js with Vite. Added: WhatsApp signature verification (WA-02), message dedup (WA-06), TTS responses (WA-08), WebSocket ticket auth, circuit breaker for LLM providers, token budget manager, automated backup strategy, observability layer (metrics, structured logging, health checks, request tracing), configurable embedding dimensions, cross-encoder reranking, memory lifecycle management, conversation summarization, tool approval persistence, Celery Beat expanded to 9 scheduled jobs, CSP/CORS headers, file upload validation, Syncthing conflict handling, TOTP lockout. Removed hardcoded secrets from Docker Compose and .env template. Replaced CSRF double-submit with SameSite=Strict explanation. Switched vector index recommendation from IVFFlat to HNSW. |
| 2.1 | 2026-07-10 | Expanded LLM provider chain to five providers: Anthropic (primary), DeepSeek (secondary), Google Gemini (tertiary), OpenAI (quaternary), Ollama (emergency local fallback). Added DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, and GEMINI_API_KEY to .env template. Updated circuit breaker, model router, tech stack, and roadmap references accordingly. |
