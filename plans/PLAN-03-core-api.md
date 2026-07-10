# PLAN-03: Core Domain APIs, WebSocket Infrastructure, Event Contract

Goal: CRUD for projects, tasks, subtasks (with changelog), conversations, messages, notifications, activity log reads, the dashboard aggregate endpoint, plus the realtime layer: Redis pub/sub, two WebSocket endpoints authenticated by single-use tickets, and the JSON event contract that PLAN-04 (Hermes) publishes and PLAN-08 (SPA) consumes.

Prerequisites: PLAN-02. Spec references: SPEC 2.2 (DASH), 2.4 (TASK/PROJ), 6.2, 6.3, 8.2, 13.1, 17.1.

## Files to create or touch

```
backend\app\schemas\__init__.py
backend\app\schemas\projects.py  tasks.py  conversations.py  notifications.py  dashboard.py
backend\app\services\project_service.py
backend\app\services\task_service.py
backend\app\services\conversation_service.py
backend\app\services\notification_service.py
backend\app\services\events.py
backend\app\routers\projects.py  tasks.py  conversations.py  notifications.py  activity.py  dashboard.py  ws.py
backend\app\main.py   (include routers)
backend\tests\test_tasks.py  test_ws.py
```

## The WS event contract (single source of truth)

Every event published to Redis and relayed over WS is a JSON object `{"type": str, "data": object}`. Channels: `conv:{conversation_id}` for chat streams, `events:{user_id}` for everything else. Types:

```
message.token      {conversation_id, message_id, delta}
message.done       {conversation_id, message_id, token_count}
tool.start         {run_id, tool, args_preview}
tool.result        {run_id, tool, ok, summary}
gate.locked        {approval_id, tool, args_preview, expires_in}
task.progress      {run_id, label, percent}
notification.new   {id, title, body, category}
task.changed       {task_id}
error              {message}
```

PLAN-04 and PLAN-09 publish these via `services\events.py`; PLAN-08 renders them. Do not invent additional types without updating this table.

## Steps in order

### Step 1: events.py

`async def publish(channel: str, event_type: str, data: dict)`: `redis.publish(channel, json.dumps({"type": event_type, "data": data}))` using a module-level `redis.asyncio` client. Also `def publish_sync(...)` with a sync client for use inside Celery workers (PLAN-09).

### Step 2: schemas

Pydantic v2 request/response models per entity, mirroring SPEC 8.2 fields. Response models always include `id` and timestamps. Enums as Python `StrEnum` matching the Postgres enums exactly (`todo`, `in_progress`, `done`, `archived`; `high`, `medium`, `low`).

### Step 3: projects router

- `POST /api/v1/projects`, `GET /api/v1/projects` (filter `is_archived=false` by default), `GET /{id}`, `PATCH /{id}`, `POST /{id}/archive`.
- `workspace_path` is stored RELATIVE to WORKSPACE_ROOT (example: `Projects/ThemisIQ`). Validate it resolves inside the sandbox using the PLAN-05 helper pattern; for now inline the same `Path.resolve` + `relative_to` check. Create the directory if missing.
- Archive hides, never deletes (PROJ-02). No hard-delete endpoint for projects.

### Step 4: tasks router and changelog (TASK-01..04)

- CRUD plus `GET /api/v1/tasks?project_id=&status=&priority=` with limit/offset (default limit 50, max 200).
- Subtasks: `POST /api/v1/tasks/{id}/subtasks`, `PATCH /api/v1/subtasks/{id}` (title or completed), `DELETE /api/v1/subtasks/{id}`.
- In `task_service.update_task`: compare old vs new for `status` and `priority`; write a `task_changelog` row per changed field IN THE SAME transaction; skip rows for unchanged fields. Touch `updated_at` explicitly is unnecessary (DB trigger covers UPDATE).
- After commit, `publish(f"events:{user_id}", "task.changed", {"task_id": str(task.id)})` and write an `activity_log` row (event_type `task_updated`, source from the request, see Step 8).

### Step 5: conversations and messages

- `POST /api/v1/conversations` (optional `project_id`, default title "New Conversation"), `GET /api/v1/conversations?project_id=&archived=`, `PATCH /{id}` (title, project link, archive), `GET /api/v1/conversations/{id}/messages?limit=&before=` returning newest-last for rendering.
- `conversation_service.append_message(conversation_id, role, content, metadata, token_count)`: inserts the message AND executes `UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = :id`. The DB trigger only fires on UPDATE of the conversations row itself; message inserts do not touch it. This helper is the single write path for messages; PLAN-04 must use it.
- Full-text search: `GET /api/v1/search/messages?q=` using `to_tsvector('english', content) @@ plainto_tsquery('english', :q)` ordered by `ts_rank` desc, limit 20, joined to conversations for titles (CHAT-07).

### Step 6: notifications and activity

- `GET /api/v1/notifications?unread_only=`, `POST /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/read-all`.
- `notification_service.notify(user_id, title, body, category)`: insert row, then publish `notification.new` on `events:{user_id}`. This is the helper every other plan calls.
- `GET /api/v1/activity?limit=&event_type=` read-only. There is NO write or delete endpoint for activity_log (SPEC 13.3, append-only).

### Step 7: dashboard aggregate (DASH-01, 02, 04, 05)

`GET /api/v1/dashboard` returns one JSON object:
- `greeting_name`, `server_time_utc`.
- `priorities`: top 5 tasks where status in (todo, in_progress), ordered priority high first then nearest due_date, nulls last.
- `recent_files`: top 5 files under WORKSPACE_ROOT by mtime: walk with `os.scandir` recursively, skip directories `.stversions`, `.git`, names starting with `.sync-conflict`, and any file over depth 6; return relative path, size, mtime. Cap the walk at 10,000 entries for the SPEC 3.1 bound.
- `running_tasks`: read Redis hash `runs:active` (PLAN-04 maintains it); empty list for now.
- `unread_notifications`: count.

### Step 8: interface origin

Add an optional header `X-Interface-Origin` (web, whatsapp, terminal, system; default web) parsed by a dependency and passed into audit logging so `activity_log.source` is accurate. Reject unknown values by defaulting to web, never 500.

### Step 9: ws.py (the ticket-consuming endpoints)

Two endpoints: `GET /ws/chat/{conversation_id}` and `GET /ws/events`, both taking `?ticket=`.

Ticket validation, BEFORE `websocket.accept()`:

```python
row = await session.execute(
    text("UPDATE ws_tickets SET used = TRUE "
         "WHERE id = :tid AND used = FALSE AND expires_at > CURRENT_TIMESTAMP "
         "RETURNING user_id"),
    {"tid": ticket},
)
```

If no row: `await websocket.close(code=4401)` and return. The atomic UPDATE...RETURNING is the single-use guarantee; SELECT-then-UPDATE is a race.

After accept: subscribe a `redis.asyncio` pubsub to the channel (`conv:{id}` after verifying the conversation belongs to the ticket's user, or `events:{user_id}`), then relay messages to the socket in a loop. Send a WS ping every 30 seconds. On `WebSocketDisconnect` or any exception: `finally:` unsubscribe and close the pubsub. Increment/decrement the `ws_connections_active` gauge.

### Step 10: ownership enforcement

Every service function takes `user_id` and filters by it in the WHERE clause (SPEC 13.1). A row that exists but belongs to nobody else can't occur in a single-user DB, but write the filters anyway; multi-user migration is a stated design constraint (SPEC 1.6). 404, not 403, when the filter misses (no existence leaks).

### Step 11: tests

- `test_tasks.py`: create, update status producing exactly one changelog row, update with no changes producing zero rows, pagination caps at 200, subtask toggle.
- `test_ws.py`: using `websockets` client inside the container: valid ticket connects and receives a published event; reused ticket gets close code 4401; expired ticket (insert with past expiry) gets 4401.

## Edge cases a weaker model would miss

1. **Accept-then-validate is wrong order.** Validate the ticket first, then `accept()`. If you accept first, close with a policy code; never leave an unauthenticated socket subscribed.
2. **Single-use tickets need the atomic UPDATE.** A SELECT followed by UPDATE lets two simultaneous connections both pass.
3. **Message inserts do not bump `conversations.updated_at`.** The trigger fires on UPDATE of conversations only. The service helper does the explicit UPDATE; every code path writing messages must go through it.
4. **Changelog only on real transitions.** PATCH with the same status must not write a row (TASK-04 tracks transitions, and noise ruins the history view).
5. **Pub/sub listeners leak.** Without the `finally: unsubscribe/close`, every reconnect leaks a Redis connection; after a day the pool is exhausted.
6. **`plainto_tsquery` not `to_tsquery`** for user input; `to_tsquery` throws syntax errors on raw text like `auth & bug(`.
7. **Recent-files walk must skip Syncthing artifacts** (`.stversions`, `.sync-conflict-*`) or the widget shows junk and PLAN-05's conflict rule is undermined.
8. **404 over 403** for other-owner rows, and archived projects must still 404 from the default list but load by direct id (UI needs to open archived detail).
9. **Never expose a DELETE for activity_log or task_changelog.** Append-only is a security property (SPEC 13.3), not a convenience.
10. **The events channel is per-user, the chat channel is per-conversation.** Publishing chat tokens to `events:{user_id}` floods every open page; keep the split exactly as the contract says.

## Acceptance criteria (verify each)

1. `pytest tests/test_tasks.py tests/test_ws.py -q` passes in the container.
2. curl CRUD round trip: create project, create task in it, PATCH status to in_progress; `task_changelog` has exactly one row; `GET /api/v1/activity` shows the task_updated event.
3. `GET /api/v1/dashboard` returns the five keys with correct shapes; with an empty workspace `recent_files` is `[]`, not an error.
4. WS smoke: obtain ticket, connect to `/ws/events?ticket=...`, then `POST /api/v1/notifications` test row via the notify helper (temporary debug route or python shell) and see `notification.new` arrive on the socket.
5. Reusing the same ticket for a second connection closes with 4401.
6. Message search returns a seeded message for a word it contains and ranks exact phrases first.
