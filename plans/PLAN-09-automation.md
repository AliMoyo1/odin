# PLAN-09: Automation Engine, Celery Beat Schedule, Encrypted Integrations

Goal: all nine scheduled jobs from SPEC 14.2, the encrypted integration credential store (SPEC 6.6, 12.2, 12.3, 12.4, 13.2), and the Cloudflare/Hetzner/GitHub clients the infra-audit and SSL jobs use. This wires already-built services (memory, summaries, WhatsApp send) into scheduled tasks and adds backups.

Prerequisites: PLAN-04, 05, 06, 07. Spec references: SPEC Doc 14, 6.6, Doc 12, 3.3 (backup), 13.2, 13.3.

## Files to create or touch

```
backend\app\services\crypto.py
backend\app\services\integration_service.py
backend\app\integrations\cloudflare.py  hetzner.py  github.py
backend\app\routers\integrations.py
backend\workers\celery_app.py          (fill beat_schedule)
backend\workers\backup_jobs.py
backend\workers\infra_jobs.py
backend\workers\maintenance_jobs.py
backend\workers\agenda_jobs.py
backend\tests\test_crypto.py  test_backup.py
```

## The nine jobs (SPEC 14.2, times in UTC)

| Cron | Task | Module |
|------|------|--------|
| `0 2 * * *` | `backup_database` | backup_jobs |
| `0 8 * * *` | `morning_agenda` | agenda_jobs |
| `0 1 * * 1` | `infra_audit` | infra_jobs |
| `0 3 * * *` | `stale_task_cleanup` | maintenance_jobs |
| `0 4 * * 0` | `memory_consolidation` | memory_jobs (PLAN-06) |
| `30 4 * * 0` | `conversation_summarize` | memory_jobs (PLAN-06) |
| `0 5 * * *` | `knowledge_reindex` | maintenance_jobs |
| `0 6 1 * *` | `ssl_cert_countdown` | infra_jobs |
| `0 23 * * *` | `ws_ticket_cleanup` | maintenance_jobs |

Celery Beat runs UTC; set `timezone = "UTC"` and `enable_utc = True` on the app so cron lines mean what they say regardless of the VPS clock.

## Steps in order

### Step 1: crypto.py (AES-256-GCM, SPEC 13.2)

`encrypt(plaintext: str) -> bytes` and `decrypt(blob: bytes) -> str` using `cryptography` AESGCM with the 32-byte key from `settings.ENCRYPTION_KEY` (base64-decoded). Layout: 12-byte random nonce prepended to ciphertext+tag. This is the SAME primitive PLAN-02 used for the TOTP secret; factor it here and have PLAN-02 import it (note the back-reference; if PLAN-02 inlined it, replace with an import now).

### Step 2: integration_service and router (SPEC 6.6)

- `set_credentials(user_id, service, creds: dict)`: `crypto.encrypt(json.dumps(creds))` into `integration_configs.credentials` (BYTEA), status `connected`, upsert on the `unique_user_service` constraint.
- `get_credentials(user_id, service) -> dict or None`: decrypt.
- `POST /api/v1/integrations/{service}` sets creds (body carries the token), `GET /api/v1/integrations` lists services with status ONLY (never returns decrypted secrets), `DELETE /api/v1/integrations/{service}` removes.
- Services: `cloudflare`, `hetzner`, `github`, plus `whatsapp` reads from env not this store. Credentials may also come from env as a fallback for single-user convenience (env wins if the DB row is absent).

### Step 3: integration clients

- `cloudflare.py`: `list_ssl_edge_certs(zone)` / `get_zone_ssl(zone)` and `recent_firewall_events(zone, hours)` via the Cloudflare v4 API with the bearer token. Read-only.
- `hetzner.py`: `list_servers()` returning name, status, and metrics (CPU, ingoing/outgoing traffic) via the Hetzner Cloud API. Read-only.
- `github.py`: `list_open_issues(repo)` and helpers; OAuth/token per SPEC 12.2. Writes (branch/PR draft) go through Hermes tools with the approval gate, not scheduled jobs.
- Each client: httpx, 15 s timeout, one retry on 5xx, and a clear typed error the jobs catch and turn into a dashboard notification rather than a crash.

### Step 4: backup_jobs.py (SPEC 3.3, the critical one)

`backup_database()`:

1. `pg_dump` via subprocess to `${BACKUP_LOCAL_DIR}/odin_YYYYMMDD_HHMMSS.sql.gz`. Do NOT shell-string the password; pass it in the child env as `PGPASSWORD` and call pg_dump with an argv list (`["pg_dump", "-h", "database-node", "-U", user, "-d", name, "-Fc"]`) piped to gzip, or use `-Fc` custom format which is already compressed. Host is the internal service name; the worker container has `postgresql-client` from the PLAN-01 image.
2. Compute SHA-256 of the file, insert a `backups` row (filename, size, checksum, offsite_synced=false).
3. Retention: delete local backups older than `BACKUP_RETENTION_DAYS` (default 30) and their `backups` rows.
4. Offsite: if `BACKUP_OFFSITE_REMOTE` is set, `rclone copy` (or rsync) the newest 7 files to the remote; on success set offsite_synced=true. Blank remote: skip offsite with a single warning, still keep local backups.
5. Notify on FAILURE only (a nightly success notification is noise); on failure send a dashboard notification AND a WhatsApp alert via the PLAN-07 client (template fallback if outside the 24 h window).

### Step 5: agenda_jobs.py (SPEC 14.2 morning agenda)

`morning_agenda()`: gather today's due and high-priority tasks, compose a short text, send via `wa_client.send_text` (which handles the 24 h window: at 08:00 the user has usually not messaged in, so this will often need the template fallback, `WHATSAPP_ALERT_TEMPLATE`). Also drop an in-app notification so it is never lost if WhatsApp send fails.

### Step 6: infra_jobs.py

- `infra_audit()` (weekly): pull Hetzner server metrics and Cloudflare firewall summaries for configured zones; if CPU sustained high, or a server is not "running", or backups appear missing on Hetzner, create a dashboard notification and (high severity only) a WhatsApp alert. Skip cleanly if those integrations are not configured.
- `ssl_cert_countdown()` (monthly): for each configured zone, check edge cert expiry; anything within 30 days creates a HIGH-priority task ("Renew SSL for <zone>, expires <date>") and sends a WhatsApp alert (SPEC 14.2).

### Step 7: maintenance_jobs.py

- `stale_task_cleanup()` (daily): tasks `done` for over 14 days move to `archived`; tasks `in_progress` untouched for 7+ days get a dashboard notification (SPEC 14.2). Use `updated_at` for the clocks.
- `knowledge_reindex()` (daily): for each processed document, stat the source file; if its mtime is newer than `indexed_at` OR the recomputed content sha differs from `content_sha256`, enqueue `index_document` (PLAN-05, idempotent). This is why PLAN-01 added those two columns.
- `ws_ticket_cleanup()` (daily): delete `ws_tickets` where `used = TRUE` OR `expires_at < now() - interval '1 hour'`.

### Step 8: fill the beat schedule

In `workers\celery_app.py`, register every task with `celery.autodiscover_tasks` or explicit imports, set `beat_schedule` from the table above using `crontab(...)`. Update the `celery_queue_depth` metric via a periodic 60 s Redis `LLEN` probe.

### Step 9: tests

- `test_crypto.py`: round-trip encrypt/decrypt; a tampered blob (flip one ciphertext byte) raises `InvalidTag` and never returns plaintext; nonce differs across two encryptions of the same input.
- `test_backup.py`: run `backup_database` against the dev DB (into a temp BACKUP_LOCAL_DIR), assert a `.sql.gz`/dump file exists with a matching sha256 row; retention deletes a planted 40-day-old file; blank offsite remote does not fail the job.

## Edge cases a weaker model would miss

1. **`PGPASSWORD` in the child env, never in the command string.** A password on the argv line leaks into `ps` and any logging of the command; string interpolation also breaks on special characters. Use `-Fc` custom format to avoid a shell pipe to gzip entirely.
2. **A backup job that only reports success is worthless.** Alert on FAILURE, and prove restore works (PLAN-10 does a restore test). An unverified backup is not a backup.
3. **Beat must run in UTC.** If the container clock is local and `enable_utc` is off, "02:00" drifts. Pin `timezone="UTC"`.
4. **Idempotent reindex needs mtime AND sha.** mtime alone re-indexes on every `touch`/Syncthing metadata change; sha alone misses same-size edits on filesystems with coarse mtime. Check mtime first (cheap), then sha to confirm (SPEC deltas).
5. **The 24-hour window bites the morning agenda hardest** (fires at 08:00 when the user is silent). Without the template fallback the daily agenda silently fails every day. Always also write the in-app notification.
6. **Integrations that are not configured must no-op, not crash Beat.** A single unhandled exception in a scheduled task can wedge the worker; wrap each job body and route failures to notifications.
7. **Never log or return decrypted credentials.** `GET /integrations` returns status only. A `__repr__` that prints the creds dict is a leak; keep secrets out of structured logs.
8. **`ws_ticket_cleanup` must keep unexpired unused tickets** (`used=TRUE OR expired`), or you delete tickets a client is about to redeem.
9. **rclone/rsync must copy only the newest 7**, not the whole directory every night (bandwidth), and offsite failure must not delete local copies.
10. **stale cleanup uses `updated_at`, not `created_at`.** A task created 20 days ago but worked on yesterday is not stale.

## Acceptance criteria (verify each)

1. `pytest tests/test_crypto.py tests/test_backup.py -q` passes.
2. Set a Cloudflare token via `POST /api/v1/integrations/cloudflare`; `GET /api/v1/integrations` shows `cloudflare: connected` and NO token value; the DB `integration_configs.credentials` column is unreadable bytes.
3. Trigger `backup_database` manually (`celery call` or a debug route): a dump file exists in `BACKUP_LOCAL_DIR`, a `backups` row has a matching checksum.
4. Plant a 40-day-old dummy backup file, rerun: it is deleted, its row gone, the fresh one kept.
5. Trigger `ssl_cert_countdown` with a zone whose cert is < 30 days out (or a stubbed client): a high-priority task is created and a WhatsApp alert is logged (dry-run).
6. Trigger `knowledge_reindex` after editing a document's source file: the document re-indexes; running it again immediately is a no-op (sha unchanged).
7. `celery -A workers.celery_app inspect scheduled` (or reading beat logs) shows all nine jobs registered.
8. `stale_task_cleanup` archives a task whose `updated_at` is 15 days old and status done; leaves a 3-day-old one alone.
