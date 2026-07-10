# PLAN-06: Memory System, Suggestions, Consolidation, Conversation Summaries

Goal: the three-tier memory behavior from SPEC Doc 10: explicit "remember" storage, vector recall injected into every Hermes turn, implicit extraction surfaced as suggestions that the user must approve, conflict handling that never overwrites explicit facts, access tracking with review, and conversation summarization that PLAN-04's budget manager consumes.

Prerequisites: PLAN-05 (embeddings infra). Spec references: SPEC Doc 10, 8.2 (memories, conversations.summary), 14.2 rows for the Sunday jobs (scheduled in PLAN-09; task bodies written here).

## Files to create or touch

```
backend\app\services\memory_service.py
backend\app\routers\memory.py
backend\app\hermes\tools\memory_tools.py   (replace stubs)
backend\app\hermes\prompt.py               (inject memories)
backend\app\hermes\loop.py                 (post-turn extraction enqueue)
backend\app\hermes\budget.py               (summary substitution, if not already wired)
backend\workers\memory_jobs.py
backend\tests\test_memory.py
```

## Memory row conventions (fixed here, used everywhere)

`memories.metadata` JSONB carries: `status` ("active", "suggested", "archived"), `origin` ("explicit", "implicit"), optional `conflict_with` (uuid), optional `suggested_from_conversation` (uuid). Only `status="active"` memories are ever injected into prompts. `key` is a short slug for explicit memories, null for implicit ones.

## Steps in order

### Step 1: memory_service.py

- `store_explicit(user_id, key, value)`: embed the value (PLAN-05 embeddings, same active model), insert with `origin=explicit, status=active`. If an ACTIVE memory with cosine distance < 0.15 already exists, UPDATE that row's value and re-embed instead of inserting a near-duplicate.
- `recall(user_id, query, k=5)`: embed query, `ORDER BY embedding <=> :qvec LIMIT :k` over `status=active` rows, FILTER out results with distance >= 0.55, return (possibly empty) list. Fire-and-forget an `UPDATE memories SET access_count = access_count + 1, last_accessed_at = now WHERE id = ANY(:ids)` (create the asyncio task, do not await it on the hot path).
- `suggest(user_id, value, conversation_id)`: embed; if distance < 0.15 to an existing ACTIVE memory, skip (duplicate); if distance < 0.30 to an existing EXPLICIT active memory but text differs, insert with `status=suggested, conflict_with=<that id>`; else insert plain `status=suggested`.
- `approve_suggestion(id)` flips to active; `reject_suggestion(id)` deletes; `archive(id)` sets archived.

### Step 2: router

- `GET /api/v1/memory?status=` list (default active), `POST /api/v1/memory` manual add, `PATCH /api/v1/memory/{id}` edit value (re-embed), `DELETE /api/v1/memory/{id}`.
- `GET /api/v1/memory/suggestions` pending list including conflict info; `POST /api/v1/memory/suggestions/{id}/approve` and `/reject`.
- `GET /api/v1/memory/review`: the monthly review payload: active memories with `access_count = 0` and `created_at` older than 90 days, plus total active count against the 1000 soft cap (SPEC 10.3).

### Step 3: Hermes wiring

- `memory_tools.py`: `remember(key, value)` calls `store_explicit` (triggered when the user says "remember that ..."; the tool description tells the model to use it for durable personal facts, not transient task info). `recall(query)` calls `recall` and returns formatted lines.
- `prompt.py`: before each turn, `recall(user_id, latest_user_message)` and inject up to 5 results as a "Known facts about the user" block with their keys. Empty result injects nothing (no empty headers).
- `loop.py` post-turn hook: after `message.done`, if the conversation now has at least 10 messages since the last extraction marker, enqueue `extract_memories(conversation_id)` (Celery). Store the marker (message count at extraction) in a Redis key `memext:{conversation_id}`.

### Step 4: implicit extraction task (SPEC 10.2)

`workers\memory_jobs.py :: extract_memories(conversation_id)`:

1. Load the last 30 messages. Call the LLM (through the PLAN-04 router, non-streaming helper, tools disabled) with an extraction prompt demanding STRICT JSON: `{"facts": [{"value": str, "confidence": "high" or "medium"}]}`, max 5 facts, only durable user facts (preferences, environment, recurring entities), never task content, never secrets or credentials.
2. `json.loads` the response; on parse failure, log and exit silently (no retry storm).
3. For each high-confidence fact: `memory_service.suggest(...)`. Medium confidence is dropped.
4. If anything was suggested, `notification.new` "Hermes noticed N things worth remembering. Review in Knowledge > Memory."

NEVER auto-activate implicit facts (SPEC 10.2: user validates first).

### Step 5: consolidation task (SPEC 10.3, scheduled Sunday in PLAN-09)

`consolidate_memories()`: compute the review payload; if the active count exceeds 1000, additionally list the least-accessed overflow. Send ONE notification linking to the review screen. This job only surfaces; archiving is a user action through the API. Mechanical cleanup it MAY do silently: delete `status=suggested` rows older than 30 days.

### Step 6: conversation summarization (SPEC 10.4, scheduled Sunday in PLAN-09, also on-demand)

`summarize_conversations()`: find conversations with 50+ messages where `summary IS NULL`, or 50+ new messages since the last summary (track the message count at summary time in a `summary_message_count` key inside conversation metadata, or a Redis key `sumct:{conversation_id}`). For each: LLM call "Summarize this conversation in under 300 words, preserving decisions, open questions, and named entities", store into `conversations.summary`.

`budget.py` consumption (verify wired per PLAN-04 Step 4): when a summary exists, prompt history = summary block + last 10 messages verbatim, replacing older history.

### Step 7: tests

`test_memory.py` with a monkeypatched deterministic embedder: explicit store then recall finds it; distance filter drops junk; near-duplicate explicit store updates in place; implicit suggestion conflicting with an explicit memory gets `conflict_with` set and does NOT alter the explicit row; approve activates; recall never returns suggested or archived rows; access_count increments after recall.

## Edge cases a weaker model would miss

1. **The retrieval threshold (distance < 0.55) is the guard against prompt poisoning by irrelevant memories.** Cosine top-k always returns SOMETHING; without the cutoff, "what time is it" injects your VPS notes into every prompt.
2. **Explicit always beats implicit** (SPEC 10.3). The conflict path must never modify the explicit row; it flags the suggestion and a human decides.
3. **The extraction call must run with tools disabled**, or the model may "helpfully" call remember() itself and bypass the suggestion gate.
4. **Extraction output is untrusted model output.** Strict JSON parse, cap 5 facts, cap value length (500 chars), and drop any fact matching a credential pattern (the words key, token, password, secret followed by a delimiter and a value).
5. **Fire-and-forget access tracking:** awaiting the UPDATE on the recall path adds latency to every chat turn for a statistic.
6. **Dedup BEFORE suggesting**, not at approval time, or the user reviews the same fact weekly forever.
7. **Summaries replace history only in the PROMPT.** Never delete or mutate message rows; the DB transcript is the audit trail.
8. **Recall must filter `status=active` in SQL**, not in Python after LIMIT, or archived rows crowd out real matches.
9. **The 10-message extraction cadence needs the marker key**, otherwise every turn past 10 messages re-extracts the whole conversation and re-suggests duplicates (the 0.15 dedup catches most, but the LLM cost is real).
10. **JSONB metadata updates in SQLAlchemy need `flag_modified` or a full dict reassignment**; mutating the dict in place does not mark the column dirty and silently persists nothing.

## Acceptance criteria (verify each)

1. `pytest tests/test_memory.py -q` passes.
2. Chat: "Remember that my VPS provider is Hetzner and my timezone is Africa/Harare". A `remember` tool call fires; the rows exist with origin explicit, status active.
3. NEW conversation: "which VPS provider do I use?" answers Hetzner without any knowledge-base document saying so; the memory's access_count incremented.
4. After a 12+ message conversation about a recurring topic, `GET /api/v1/memory/suggestions` shows at least one suggestion and a notification arrived; approving it makes it active; it now appears in recall.
5. Seed an explicit memory "editor: VS Code", then force a suggestion "editor: vim" (call suggest directly): the suggestion carries `conflict_with`, the explicit row is untouched, the suggestions endpoint shows the conflict.
6. Seed a conversation with 55 short messages, run `summarize_conversations` manually: `conversations.summary` fills; a subsequent chat turn's budget metadata shows history tokens dropped (summary in use).
7. `GET /api/v1/memory/review` lists a seeded stale memory (access_count 0, created 100 days ago via SQL seed).
