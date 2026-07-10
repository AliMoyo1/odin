# PLAN-04: Hermes AI Core, Five-Provider Router, Circuit Breaker, ReAct Loop, Approval Gate

Goal: the Hermes execution core. A normalized provider layer over DeepSeek (primary), Anthropic, Google Gemini, OpenAI, and Ollama; a circuit breaker with automatic failover; a token budget manager; the ReAct loop with tool calling, streaming into the PLAN-03 event contract; and the GATE_LOCKED approval flow with persisted auto-approvals.

Prerequisites: PLAN-03. Spec references: SPEC 3.3 (resilience), 4.3, Doc 09, 17.1.

## Files to create or touch

```
backend\app\hermes\__init__.py
backend\app\hermes\types.py
backend\app\hermes\providers\__init__.py
backend\app\hermes\providers\base.py
backend\app\hermes\providers\anthropic_provider.py
backend\app\hermes\providers\openai_compat.py      (serves DeepSeek, OpenAI, Ollama)
backend\app\hermes\providers\gemini_provider.py
backend\app\hermes\breaker.py
backend\app\hermes\router.py
backend\app\hermes\budget.py
backend\app\hermes\prompt.py
backend\app\hermes\loop.py
backend\app\hermes\gate.py
backend\app\hermes\tools\__init__.py
backend\app\hermes\tools\registry.py
backend\app\hermes\tools\task_tools.py
backend\app\hermes\tools\file_tools.py     (thin now, real sandbox arrives in PLAN-05)
backend\app\hermes\tools\kb_tools.py       (stub returning "knowledge base not installed yet")
backend\app\hermes\tools\memory_tools.py   (stub, real in PLAN-06)
backend\app\routers\chat.py
backend\app\routers\approvals.py
backend\scripts\provider_smoke.py
backend\tests\test_breaker.py  test_budget.py  test_gate.py
```

## Architecture decisions fixed by this plan

- The agent turn runs as an `asyncio.create_task` inside the API process (single user; no Celery hop for chat). The POST returns 202 immediately per SPEC 17.1; tokens arrive over WS.
- Internal normalized types in `types.py`: `ChatMessage(role, content)`, `ToolCall(id, name, arguments: dict)`, `ToolSpec(name, description, input_schema: dict, requires_approval: bool)`, and stream events `TextDelta(text)`, `ToolCallReady(call)`, `TurnDone(stop_reason, usage)`.
- Providers never raise into the loop: they raise `ProviderError(provider, retriable: bool, message)` and the router decides.

## Steps in order

### Step 1: provider base and the three adapters

`base.py`: `class Provider(Protocol)` with `name: str`, `configured: bool`, and `async def stream_turn(system: str, messages: list[ChatMessage], tools: list[ToolSpec], max_tokens: int) -> AsyncIterator[TextDelta or ToolCallReady or TurnDone]`.

**anthropic_provider.py** (secondary failover). Uses the `anthropic` SDK directly. Model from `settings.HERMES_MODEL_ANTHROPIC` (default `claude-opus-4-8`), adaptive thinking, streaming:

```python
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

stream = await client.messages.create(
    model=settings.HERMES_MODEL_ANTHROPIC,
    max_tokens=max_tokens,
    system=system,
    messages=api_messages,
    tools=[t.as_anthropic() for t in tools],
    thinking={"type": "adaptive"},
    stream=True,
)
```

Translate `content_block_delta` text deltas to `TextDelta`, accumulate `tool_use` blocks (id, name, streamed `input_json_delta` fragments joined then `json.loads`) into `ToolCallReady`, and `message_stop` into `TurnDone`. IMPORTANT: keep the raw assistant content blocks (including any thinking blocks) verbatim on the turn state; when the loop sends tool results back, the prior assistant message must contain those blocks exactly as received.

**openai_compat.py** (one class, three instances). DeepSeek (primary), OpenAI, and Ollama all speak the OpenAI Chat Completions protocol. Construct with `(name, api_key, base_url, model)`:

- DeepSeek: `base_url=settings.DEEPSEEK_BASE_URL` (`https://api.deepseek.com`), model `deepseek-chat`.
- OpenAI: default base_url, model `settings.OPENAI_MODEL`.
- Ollama: `base_url=settings.OLLAMA_BASE_URL + "/v1"`, `api_key="ollama"` (any non-empty string), model `settings.OLLAMA_MODEL`.

Use `openai.AsyncOpenAI(...).chat.completions.create(..., stream=True, tools=openai_tools)`. Tool calls arrive as fragmented deltas: accumulate by `tool_call.index`, concatenating `function.arguments` string fragments, and only emit `ToolCallReady` after `finish_reason == "tool_calls"`. Map ToolSpec to `{"type": "function", "function": {"name", "description", "parameters": input_schema}}`. System prompt becomes the first message with role `system`. Tool results are sent as role `tool` messages with `tool_call_id`.

**gemini_provider.py**. Uses the `google-genai` SDK (`from google import genai`). Build `genai.Client(api_key=settings.GEMINI_API_KEY)` and call `client.aio.models.generate_content_stream(model=settings.GEMINI_MODEL, contents=..., config=...)` with `function_declarations` built from ToolSpec. Before passing schemas, run them through a sanitizer that strips keys Gemini rejects: `additionalProperties`, `$schema`, `format` values other than the ones Gemini supports (keep `enum`, `date-time`). Map conversation history to Gemini `contents` roles (`user` and `model`); tool results are sent as `function_response` parts. If any SDK call shape fails at runtime, consult the official google-genai docs and adjust the adapter only; the normalized interface must not change.

### Step 2: breaker.py (SPEC 3.3, 4.3)

Per-provider in-memory state plus persistence to `llm_provider_health`:

- Counters: `consecutive_failures`, `circuit_open`, `circuit_opened_at`.
- A call that raises, or exceeds a 30-second per-call timeout (`asyncio.timeout(30)` around first token, then a 120-second total-stream guard), counts as a failure. 3 consecutive failures opens the circuit.
- Open circuit: skip the provider. After 60 seconds, half-open: allow exactly one trial call; success closes and zeros the counter, failure re-opens.
- Every transition and every call outcome updates the `llm_provider_health` row (upsert by provider) and the `llm_calls_total{provider,outcome}` metric. Decisions are made from memory; the table is for observability, never read on the hot path.

### Step 3: router.py

Ordered chain: deepseek, anthropic, gemini, openai, ollama. `stream_with_failover(...)`:

1. Build the list of candidates: configured (key present) AND circuit not open (or half-open trial allowed).
2. Try each in order. A provider failure BEFORE any text delta has been emitted: record failure, move to the next candidate silently.
3. A failure AFTER text has streamed: record it, publish an `error` event with a short message, and end the turn; do not replay half-answered prompts on a second provider (duplicate side effects risk).
4. If no candidate remains, publish `error` with "all providers unavailable" and mark the turn failed.
5. Every response records which provider served it in the assistant message `metadata` (`{"provider": name, "model": model}`).

### Step 4: budget.py (SPEC 4.3 token budget)

Estimator: `len(text) // 4 + 8` per message (fast, provider-agnostic). Budget input: model context limit (per provider config, default 64000 for deepseek-chat, 200000 for Anthropic, 1000000 for Gemini 2.5, 128000 for OpenAI, 8192 for Ollama), reserve `max_tokens` (default 4096) for output. Assembly order and trim policy:

1. System persona (never trimmed).
2. Injected memories (cap 5 entries, PLAN-06).
3. RAG chunks (cap 5; trim first, down to 3 then 0).
4. Conversation history (newest kept; oldest turns dropped first; if a summary exists in `conversations.summary`, replace everything older than the last 10 messages with the summary, see PLAN-06).

Return the breakdown dict used in the POST response metadata (SPEC 17.1 shape).

### Step 5: prompt.py

`build_system_prompt(user, project, memories, rag_chunks)`: persona ("You are Hermes, the AI core of ODIN..."), absolute date, user timezone, active project block (name, workspace path, description) when linked (CHAT-04), memory block, RAG block with citation markers `[Source: filename, p.N]` and the instruction to cite (SPEC 15.2), and the tool-conduct rules (destructive actions require approval; never fabricate file contents).

### Step 6: tools

`registry.py`: `@tool(name, description, requires_approval=False)` decorator registering a Pydantic input model + async handler; produces ToolSpec (JSON schema via `model_json_schema()`) and dispatch. Handlers call SERVICES directly (task_service etc.), never HTTP.

Initial set:
- `create_task(title, description?, project_id?, priority?, due_date?)`
- `update_task(task_id, status?, priority?, due_date?, title?)`
- `list_tasks(project_id?, status?)`
- `list_projects()`
- `list_files(path?)` and `read_file(path, max_bytes=20000)`: for now restricted to WORKSPACE_ROOT with the resolve/relative_to check inline; PLAN-05 replaces the internals with file_service.
- `write_file(path, content)`: `requires_approval=True`.
- `search_knowledge(query)`: stub answer until PLAN-05.
- `remember(key, value)` and `recall(query)`: stubs until PLAN-06.

Every tool result is coerced to a string of at most 4000 estimated tokens (truncate with a `[truncated]` marker). Handler exceptions are caught by the dispatcher and returned to the model as `{"ok": false, "error": "<class>: <message>"}`; never a raw traceback, never a crash of the loop.

### Step 7: loop.py (the ReAct loop, SPEC 9.1)

`async def run_turn(user, conversation_id, user_message_id)`:

1. Load history via conversation_service, build budgeted prompt (Steps 4, 5).
2. Register run in Redis hash `runs:active` (run_id, label, started_at); remove in `finally`.
3. Iterate: call `router.stream_with_failover`. Relay `TextDelta` as `message.token` events (buffer and flush every ~50 ms so WS is not flooded per-token).
4. On `ToolCallReady`: publish `tool.start`. If the tool `requires_approval` and no matching `tool_approvals` row with `auto_approve=TRUE` exists (match on user_id + tool_name + project_id), enter the gate (Step 8) and STOP this turn. Otherwise execute, publish `tool.result`, append the tool result message, and continue the loop.
5. Hard cap: 8 tool iterations per turn. On hitting it, append a system nudge "iteration budget exhausted, summarize what you have" and do one final call with no tools.
6. Repeated-call guard: if the same tool with identical arguments is requested twice in a row, return the previous result with a note instead of executing again.
7. On `TurnDone`: persist the assistant message via `conversation_service.append_message` with token_count and provider metadata, publish `message.done`.

### Step 8: gate.py (GATE_LOCKED, SPEC 9.1)

- On gated tool: create `approval_id = uuid4`, store the full pending state in Redis key `gate:{approval_id}` with TTL 600: conversation_id, provider snapshot of messages so far (including the assistant content blocks that contain the tool_use), the ToolCall, user_id, project_id.
- Publish `gate.locked {approval_id, tool, args_preview, expires_in: 600}` and persist an assistant-visible marker message (role system, content "Awaiting approval for write_file ...", metadata carries approval_id) so the state survives a page reload.
- `POST /api/v1/approvals/{approval_id}/approve` with optional body `{"remember": true}`: load and DELETE the Redis key atomically (`GETDEL`), execute the tool, and resume the loop with the stored state in a fresh asyncio task. If `remember` is true, upsert a `tool_approvals` row with `auto_approve=TRUE`.
- `POST /api/v1/approvals/{approval_id}/deny`: delete the key, append a tool result "denied by user", resume the loop so the model can react.
- Expired approval_id: 410 Gone.

### Step 9: chat router (SPEC 17.1)

`POST /api/v1/chat/message` `{conversation_id, content, interface_origin}`: persist the user message, spawn `run_turn`, return 202 `{message_id, status: "queued_for_generation", metadata: {active_project, injected_memory_count, token_budget}}`. Also `POST /api/v1/chat/stop/{conversation_id}`: cancel the active run task cleanly (publish `message.done` with what streamed so far).

### Step 10: readiness and smoke

- Extend `/health/ready`: `llm_provider` reports the first configured provider whose circuit is closed (SPEC 17.1 example shape).
- `scripts\provider_smoke.py`: for each configured provider, one tiny non-tool prompt ("Reply with the word ok"), printing provider, latency, first 40 chars. Skips unconfigured providers with a SKIP line, never a failure.

### Step 11: tests

- `test_breaker.py`: 3 failures open, skip while open, half-open after 60 s (monkeypatch clock), success closes.
- `test_budget.py`: history trimming order, RAG trim 5 to 3, summary substitution.
- `test_gate.py`: gated tool produces gate.locked and a Redis key; approve executes and resumes; deny resumes with denial; expiry returns 410; `remember: true` writes tool_approvals and the next identical call skips the gate.

## Edge cases a weaker model would miss

1. **OpenAI-compatible tool-call arguments stream in fragments** keyed by `index`, not `id`. Concatenate strings per index and parse JSON only at finish. Parsing each fragment crashes every time.
2. **Anthropic tool results must follow an assistant message containing the original content blocks** (including thinking blocks) exactly as received. Reconstructing the assistant message from plain text breaks tool use and violates thinking-block replay rules.
3. **Gemini rejects JSON Schema keys like `additionalProperties`.** Sanitize schemas per provider; do not hand one schema dict to all three SDK formats.
4. **Do not failover mid-stream.** Once text reached the user, a retry on another provider re-executes reasoning and can re-fire tools. Fail the turn visibly instead.
5. **An unconfigured provider (missing key) is "skipped", never "failed".** Otherwise the breaker table fills with junk and `/health/ready` lies.
6. **The 30-second timeout is to FIRST token**, with a separate longer whole-stream guard. A single timeout on the whole stream kills every long answer.
7. **Never put the pending tool execution inside the WS handler or block the loop waiting for approval.** The turn ENDS at gate.locked; approval starts a NEW task from persisted state. Blocking coroutines die on reload and deadlock shutdown.
8. **`GETDEL` (or a Lua/`pipeline` equivalent) for approval consumption.** Plain GET then DELETE lets a double-click execute a destructive tool twice.
9. **Ollama needs a dummy api_key** ("ollama"); the openai SDK refuses an empty string.
10. **Buffer token events.** Publishing every single delta as its own Redis message and WS frame melts the browser at Opus streaming speeds; 50 ms flushes look identical to the user.
11. **Auto-approval matching must include project_id** (NULL-safe compare). A write_file approval remembered inside project A must not silently authorize writes in project B (SPEC 9.1 scoping).
12. **deepseek-reasoner does not support function calling; keep `deepseek-chat`** as the DeepSeek model for tool turns.
13. **Cancellation:** `run_turn` must handle `asyncio.CancelledError` by persisting the partial assistant text before re-raising, or stop loses the streamed content.

## Acceptance criteria (verify each)

1. `pytest tests/test_breaker.py tests/test_budget.py tests/test_gate.py -q` passes.
2. With a valid DEEPSEEK_API_KEY: WS script connects, POST a chat message "Create a task called Buy milk with high priority", tokens stream, `tool.start` and `tool.result` events appear, the task row exists, `message.done` closes, and the assistant message row records `{"provider": "deepseek"}`.
3. Ask "write a file called notes/test.txt with content hello": `gate.locked` arrives; approving via curl executes and the file exists under `workspace\notes\`; the resumed answer streams.
4. Same request again after approving with `remember: true`: no gate, file written directly.
5. Break the DeepSeek key (one wrong char), restart the API: with a valid ANTHROPIC_API_KEY (or GEMINI) the same chat works and metadata records the fallback provider; `llm_provider_health` shows deepseek failures and circuit_open TRUE after 3 attempts.
6. `python scripts/provider_smoke.py` prints one line per configured provider with latency.
7. `POST /api/v1/chat/stop/{id}` during a long answer stops the stream and the partial text is persisted.
