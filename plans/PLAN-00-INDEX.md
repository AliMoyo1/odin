# PLAN-00: ODIN Build Index and Execution Order

Written 2026-07-10. Source of truth: `..\SPEC.md` (ODIN Master Specification v2.1). All plans live in this folder. The project is built inside `C:\Users\isadmin\Desktop\Odin`.

## What ODIN is

A single-user personal AI operating environment. FastAPI monolith, PostgreSQL 15+ with pgvector, Redis, Celery, Vite + React SPA, Hermes AI core with a five-provider failover chain (Anthropic primary, DeepSeek, Gemini, OpenAI, Ollama), WhatsApp gateway, Syncthing-watched workspace, RAG knowledge base, three-tier memory.

## Target folder layout (created by the plans)

```
Odin\
  SPEC.md                  The specification (already present)
  plans\                   These plan files (already present)
  backend\                 FastAPI app, Celery workers, Alembic, tests
  frontend\                Vite + React SPA
  workspace\               Dev stand-in for the /ODIN synced root
  keys\                    RS256 JWT keypair (gitignored)
  docker-compose.dev.yml
  docker-compose.prod.yml  (written in PLAN-10)
  .env.example
  .env                     (gitignored, never committed)
```

## The plans

| # | File | Delivers | Depends on |
|---|------|----------|------------|
| 01 | PLAN-01-foundation.md | Repo scaffold, Docker dev stack, full DB schema via Alembic, config, structured logging, request IDs, /health, /metrics | nothing |
| 02 | PLAN-02-auth.md | RS256 JWT, refresh cookie sessions, TOTP 2FA with lockout, rate limiting, WS tickets, seed user script | 01 |
| 03 | PLAN-03-core-api.md | Projects, tasks, subtasks, changelog, conversations, notifications, activity log, dashboard aggregate, WebSocket infrastructure and event contract | 02 |
| 04 | PLAN-04-hermes-core.md | Model router (5 providers), circuit breaker, token budget, ReAct loop, tool registry, GATE_LOCKED approvals, streaming | 03 |
| 05 | PLAN-05-knowledge-rag.md | Sandboxed file service, upload validation, extraction, chunking, embeddings, pgvector search, optional rerank, citations, watchdog | 04 |
| 06 | PLAN-06-memory.md | Explicit and implicit memories, retrieval injection, suggestions with approval, consolidation, conversation summarization | 05 |
| 07 | PLAN-07-whatsapp.md | Webhook with HMAC verify, dedup, Whisper voice notes, TTS replies, proactive sends. Go-live section runs only after PLAN-10 | 04 (05 improves it) |
| 08 | PLAN-08-frontend.md | Full SPA: login with TOTP, dashboard, streaming chat with approvals, tasks, files, knowledge | 03 (full value after 04) |
| 09 | PLAN-09-automation.md | All 9 Celery Beat jobs (backup, agenda, infra audit, stale tasks, memory consolidation, summarize, reindex, SSL countdown, ticket cleanup), encrypted integrations (Cloudflare, Hetzner, GitHub) | 04, 05, 06, 07 |
| 10 | PLAN-10-deployment.md | Production compose, nginx server block on the existing Hetzner VPS beside ThemisIQ, TLS, backups dir, restore test, WhatsApp go-live | all |
| 11 | PLAN-11-voice.md | TTS endpoint (OpenAI tts-1-hd, voice onyx), browser STT with wake word "Hermes", always-listening toggle, sentence-streaming queue, three-state orb (idle/listening/speaking), Firefox push-to-talk fallback | 03, 04, 08 |

## Ranking by leverage (impact per unit of effort)

1. **PLAN-01 foundation.** Everything else is blocked without it. The schema migration alone unblocks 9 plans.
2. **PLAN-02 auth.** Every protected route, the WS ticket flow, and the frontend login depend on it.
3. **PLAN-03 core API.** The data spine plus the WS event contract that Hermes and the SPA both speak.
4. **PLAN-04 Hermes core.** The reason the product exists. Once this works you have an AI assistant, even if only via curl and a WS script.
5. **PLAN-08 frontend.** Usability multiplier: turns a curl-only backend into a daily driver.
6. **PLAN-05 knowledge RAG.** The differentiator: answers grounded in your own documents with citations.
7. **PLAN-06 memory.** Makes Hermes feel personal; cheap once 05 exists because embeddings infra is shared.
8. **PLAN-07 WhatsApp.** High value but gated on external Meta setup and a public URL.
9. **PLAN-09 automation.** Proactive value; mostly wiring existing services into scheduled jobs.
10. **PLAN-10 deployment.** Zero new features, but nothing is real until it runs on the VPS.

## Recommended execution order

01, 02, 03, 04, 08, 05, 06, 07 (build and local tests only), 09, 10, then the go-live section at the end of 07.

Rationale: after 04 + 08 you have a usable product loop on localhost (chat, tasks, approvals). 05 and 06 deepen it. 07 is written and tested locally with simulated signed payloads; its Meta wiring needs the public HTTPS URL that only exists after 10. 09 needs 07's send client for the morning agenda job, so it comes after.

## Deliberate deltas from SPEC.md (do not "fix" these back)

1. **embedding_config unique constraint.** SPEC 8.1 says `UNIQUE (is_active)`. That caps the table at two rows total (one TRUE, one FALSE). Implemented instead as a partial unique index: `CREATE UNIQUE INDEX one_active_embedding_config ON embedding_config (is_active) WHERE is_active = TRUE;`
2. **knowledge_documents gets two extra columns**, `indexed_at TIMESTAMP WITH TIME ZONE` and `content_sha256 VARCHAR(64)`. The daily `knowledge_reindex` job (SPEC 14.2) is impossible to implement idempotently without them.
3. **WORKSPACE_ROOT env var** replaces the hardcoded `/home/ali/ODIN` everywhere. Dev on Windows binds `.\workspace` into containers at `/data/ODIN`.
4. **Sandbox checks use `Path.resolve()` plus `relative_to()`**, not `startswith` as sketched in SPEC 11.2. `startswith("/home/ali/ODIN")` lets `/home/ali/ODIN2` through.
5. **Proactive WhatsApp sends outside Meta's 24-hour service window require an approved template message.** SPEC WA-05 is silent on this. PLAN-07 and PLAN-09 handle it.
6. **Rerank is optional behind RERANK_ENABLED** (default off). The cross-encoder pulls torch (~800 MB) which is unreasonable on the shared VPS by default.

## Global conventions (apply to every plan)

- Python 3.12, full type hints (SPEC Doc 19), async SQLAlchemy sessions inside `async with` blocks.
- Never commit secrets. `.env`, `keys\`, `workspace\`, `node_modules\`, `dist\` are gitignored. `.env.example` carries placeholder values only.
- DeepSeek is the primary LLM provider (model `deepseek-chat`). Failover order: Anthropic (`claude-opus-4-8`, adaptive thinking), Gemini (`gemini-2.5-flash`), OpenAI (`gpt-4o`), Ollama (`llama3.1:8b`). All env-overridable. Deepseek-reasoner does NOT support function calling; use `deepseek-chat` for all tool turns.
- Every command shown in a plan is a single copy-pasteable command. No command contains the pipe character. Never bundle two commands with `&&` in a step.
- No em dashes in any file, comment, or UI copy this project produces. Use a colon, comma, or period.
- API base path is `/api/v1`. WS endpoints live under `/ws`. Frontend always calls relative URLs.
- Visual design source of truth is `..\Design\`: the "Kinetic Command" system (DESIGN.md tokens, four HTML mockups, orb render). PLAN-08 encodes it: deep matte black, vibrant orange, glassmorphism panels (`rgba(26,26,26,0.6)` + 12px backdrop blur + orange-tinted 1px border), JetBrains Mono + Inter, breathing Hermes orb. Mockup `code.html` files are ground truth; their embedded Tailwind config wins over DESIGN.md where they disagree. Never carry the mockups' CDN links (Google Fonts, Tailwind CDN, googleusercontent images) into the app; production CSP blocks external origins.
- The executor works from `C:\Users\isadmin\Desktop\Odin` unless a step says otherwise. VPS steps in PLAN-10 run on the server.
- When a plan says "SPEC 8.2" it means that numbered section inside `..\SPEC.md`.

## How to execute a plan (instructions for the executing model)

1. Read this index, then the plan file top to bottom, then the SPEC sections it cites.
2. Do the steps strictly in order. Do not skip acceptance criteria.
3. If a step's output contradicts the plan, stop and record the discrepancy in the Work log below; do not improvise around schema or security steps.
4. After finishing a plan, run its acceptance list, then append a dated line to the Work log.

## Work log

- 2026-07-10: Index created. All ten plans (PLAN-01 through PLAN-10) written. Ready for execution starting at PLAN-01.
- 2026-07-10: Design files added to `..\Design\` (Kinetic Command). PLAN-08 rewritten to encode the design system: glassmorphism recipe, ambient glow layer, Hermes orb, GATE_LOCKED modal spec, four-column task board, per-page visual specs, design-specific edge cases and acceptance checks.
- 2026-07-10: PLAN-11 written. Voice interface: TTS via OpenAI tts-1-hd (voice onyx), browser SpeechRecognition with "Hermes" wake word, always-listening toggle persisted to localStorage, sentence-streaming TTS queue, three-state orb animation, Firefox MediaRecorder fallback to Whisper.
