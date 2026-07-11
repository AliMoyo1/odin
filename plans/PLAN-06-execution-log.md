# PLAN-06 Execution Log

## Status: COMPLETE

## Steps

- [x] Step 1: memory_service.py (store_explicit, recall, suggest, approve/reject/archive, list_memories, get_stale_memories, count_active)
- [x] Step 2: router (CRUD, suggestions, review) - app/routers/memory.py
- [x] Step 3: Hermes wiring (memory_tools, prompt injection, loop post-turn hook + _maybe_enqueue_extraction)
- [x] Step 4: extract_memories Celery task - workers/memory_jobs.py
- [x] Step 5: consolidate_memories task - workers/memory_jobs.py
- [x] Step 6: summarize_conversations task + beat schedule - workers/memory_jobs.py + celery_app.py
- [x] Step 7: tests - tests/test_memory.py (9 tests covering store, recall, suggest, approve, reject, archive)

## Changes made

### Step 1
- Created backend/app/services/memory_service.py
  - store_explicit: embed + near-duplicate dedup (< 0.15) + update or insert
  - recall: embed query + pgvector cosine search with 0.55 cutoff, fire-and-forget access tracking
  - suggest: credential filter, near-dup skip (< 0.15), conflict detection (< 0.30), insert as suggested
  - approve_suggestion, reject_suggestion, archive, list_memories, get_stale_memories, count_active

### Step 2
- Created backend/app/routers/memory.py
  - GET /api/v1/memory (list by status)
  - POST /api/v1/memory (create explicit)
  - PATCH /api/v1/memory/{id}
  - DELETE /api/v1/memory/{id}
  - GET /api/v1/memory/suggestions
  - POST /api/v1/memory/suggestions/{id}/approve
  - POST /api/v1/memory/suggestions/{id}/reject
  - GET /api/v1/memory/review

### Step 3
- Replaced stub in backend/app/hermes/tools/memory_tools.py with real service calls
- Updated backend/app/hermes/prompt.py: "Known facts about the user:" label
- Updated backend/app/hermes/loop.py:
  - Load conv_summary and call recall() before building system prompt
  - Build system prompt with recalled memories
  - After message.done: call _maybe_enqueue_extraction()
  - Added _maybe_enqueue_extraction helper (Redis memext:{conv_id} marker, cadence 10)

### Step 4-6
- Created backend/workers/memory_jobs.py:
  - extract_memories(conversation_id): last 30 msgs, LLM strict JSON, high-confidence facts -> suggest(), notification
  - consolidate_memories(): per-user cleanup, delete stale suggestions (30+ days), surplus warning
  - summarize_conversations(): 50+ message convs without summary, LLM summarize, store to conversations.summary
  - _llm_call_no_tools(): single-shot LLM call via stream_with_failover, tools=[]
- Updated backend/workers/celery_app.py: include workers.indexing + workers.memory_jobs, beat schedule for consolidate (daily 03:00) and summarize (every 2h)

### Step 7
- Created backend/tests/test_memory.py (9 acceptance tests)

### Supporting changes
- Added extra_meta field to Memory model in backend/app/models/models.py (was missing, used by service)
- Created backend/alembic/versions/0004_memories_metadata.py: adds metadata JSONB column to memories
- Added memory_router to backend/app/main.py
