# PLAN-10: Production Deployment on the Existing Hetzner VPS (beside ThemisIQ)

Goal: run ODIN on the same Hetzner VPS that already hosts ThemisIQ, on its own subdomain, as its own Docker Compose stack behind the existing nginx, with TLS, working backups, a verified restore, and the WhatsApp channel live. Zero disruption to ThemisIQ.

Prerequisites: PLAN-01 through 09 built and green locally. Spec references: SPEC Doc 16, 3.3 (backup/restore), 3.4.

## Constraints for every command in this plan

- One command per step. Never two commands joined by `&&`. Never a pipe character in a command the operator types (they cannot type it in the Hetzner web console).
- Where a pipeline would normally be used, this plan gives a script file the operator runs, or a single tool invocation, so no typed pipe is needed.
- Secrets are typed into the server `.env` with a text editor, never committed, never echoed into shell history where avoidable.

## Files to create

```
docker-compose.prod.yml
backend\Dockerfile           (production, no --reload, gunicorn/uvicorn workers)
nginx\odin.conf              (server block, copied to the VPS nginx)
scripts\restore_test.sh      (restore latest backup into a scratch DB and count tables)
DEPLOY.md                    (this runbook, condensed, kept in the repo)
```

## Part A: coexistence check (do first, do not skip)

ODIN must not collide with ThemisIQ on ports, container names, networks, or the DB.

### Step 1: see what ThemisIQ already uses

Run on the VPS: `docker ps --format "{{.Names}} {{.Ports}}"`

Record the host ports in use. ThemisIQ (per memory) runs as `themisiq-app.service` with its own Postgres. ODIN will use DIFFERENT host ports and its OWN Postgres container, sharing nothing.

### Step 2: confirm nginx is the host reverse proxy

Run: `systemctl status nginx`

If nginx runs on the host (it serves ThemisIQ), ODIN adds a server block to it. If ThemisIQ terminates TLS itself in a container, ODIN instead uses its own nginx container on a free port and you point DNS at it; decide based on what Step 2 shows and note the choice in DEPLOY.md.

## Part B: DNS and the subdomain

### Step 3: create the DNS record

In Cloudflare, add an A record `odin` pointing to the VPS IP, proxied (orange cloud) if ThemisIQ already is, so the pattern matches.

### Step 4: pick the domain variable

Decide the hostname (example `odin.themisiq.net` or a personal domain). Use it consistently below as YOUR_DOMAIN.

## Part C: production compose and images

### Step 5: production Dockerfile

`backend\Dockerfile`: same as dev but no bind mount of source, no `--reload`, run `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`. Copy the code in. Keep ffmpeg and postgresql-client.

### Step 6: docker-compose.prod.yml

Differences from dev:
- No source bind mounts; images are built.
- Postgres host port bound to `127.0.0.1:5434` only (loopback, never public). Redis not published at all (internal network only).
- The `frontend` build (PLAN-08 Dockerfile) produces static files served by ODIN's nginx OR copied to the host nginx docroot (per Step 2 decision).
- Named volume `odin_prod_db` for Postgres, bind `/opt/odin/workspace` for the workspace, bind `/opt/odin/backups` for backups, `/opt/odin/keys` read-only for the JWT keys.
- `restart: unless-stopped` on every service.
- `WATCHER_FORCE_POLLING=0` (real inotify on Linux).
- Worker and beat run as separate services as in dev.

### Step 7: get the code onto the VPS

Run: `git clone YOUR_REPO_URL /opt/odin`

If the repo is private and no deploy key is set, instead create `/opt/odin` and copy the tree up with scp; note which in DEPLOY.md. Do not put `.env` in the repo; it is created next.

### Step 8: create the production .env on the server

Run: `cp /opt/odin/.env.example /opt/odin/.env`

Then edit `/opt/odin/.env` with nano and fill REAL values:
- `ENVIRONMENT=prod`
- `SECRET_KEY` and `ENCRYPTION_KEY`: generate locally and paste (Step 9).
- DB creds (a strong password), `DATABASE_URL` pointing at `database-node:5432`.
- `CORS_ALLOWED_ORIGIN=https://YOUR_DOMAIN`.
- LLM keys (at least ANTHROPIC_API_KEY; DeepSeek, Gemini, OpenAI as available).
- WhatsApp values stay blank until Part F. `WA_DRY_RUN=1` for now.

### Step 9: generate secrets locally, paste into .env

On your workstation run: `python -c "import secrets; print(secrets.token_hex(32))"` for SECRET_KEY.

For ENCRYPTION_KEY run: `python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"`

Paste both into the server `.env`. Never commit them.

### Step 10: generate the JWT keypair on the server

Run: `mkdir -p /opt/odin/keys`

Then run: `docker compose -f /opt/odin/docker-compose.prod.yml run --rm gateway-api python scripts/generate_keys.py /keys`

Confirm `/opt/odin/keys/jwt_private.pem` and `jwt_public.pem` exist and are NOT world-readable.

## Part D: bring it up

### Step 11: build

Run: `docker compose -f /opt/odin/docker-compose.prod.yml build`

### Step 12: start the data services first

Run: `docker compose -f /opt/odin/docker-compose.prod.yml up -d database-node redis-broker`

### Step 13: migrate

Run: `docker compose -f /opt/odin/docker-compose.prod.yml run --rm gateway-api alembic upgrade head`

### Step 14: start everything

Run: `docker compose -f /opt/odin/docker-compose.prod.yml up -d`

### Step 15: create the user

Run: `docker compose -f /opt/odin/docker-compose.prod.yml exec gateway-api python scripts/create_user.py --email alimoyo58@gmail.com --name Ali --password A_STRONG_PASSWORD`

## Part E: nginx and TLS

### Step 16: install the server block

Copy `nginx/odin.conf` to the host: `cp /opt/odin/nginx/odin.conf /etc/nginx/sites-available/odin.conf`

The server block: `server_name YOUR_DOMAIN;` proxying `/` to the SPA static root (or the frontend container), `/api/` and `/ws/` to `127.0.0.1:8000` with the WebSocket upgrade headers, `/metrics` restricted to localhost only (never public). It sets the CSP, HSTS, and `X-Frame-Options: DENY` headers from SPEC 13.2. Max body size 60m to allow the 50 MB uploads.

### Step 17: enable the site

Run: `ln -s /etc/nginx/sites-available/odin.conf /etc/nginx/sites-enabled/odin.conf`

### Step 18: test the nginx config

Run: `nginx -t`

### Step 19: reload nginx

Run: `systemctl reload nginx`

### Step 20: issue the TLS certificate

If certbot handles ThemisIQ, run: `certbot --nginx -d YOUR_DOMAIN`

If Cloudflare origin certs are the pattern (proxied orange-cloud), install the origin cert files instead and set SSL mode Full (strict); match whatever ThemisIQ does. Note the choice in DEPLOY.md.

## Part F: WhatsApp go-live (PLAN-07 Part 9)

Only now, with a public HTTPS URL, execute PLAN-07 Step 9 in order: fill the WhatsApp env values on the server, set `WA_DRY_RUN=0`, restart the stack (`docker compose -f /opt/odin/docker-compose.prod.yml up -d`), register and verify the webhook in the Meta console, subscribe to `messages`, and confirm a real reply. Do not enable this before TLS is green.

## Part G: backups and the restore test (SPEC 3.3, the part everyone skips)

### Step 21: confirm the nightly backup ran

After the first 02:00 UTC (or trigger it manually), run: `ls -la /opt/odin/backups`

A dated dump file must be present and a `backups` DB row must exist.

### Step 22: run the restore test

`scripts/restore_test.sh` (a FILE, so no typed pipe): creates a scratch database, restores the newest dump into it with `pg_restore`, counts tables, prints PASS if the count matches the live schema (19+), then drops the scratch DB. Run it: `bash /opt/odin/scripts/restore_test.sh`

A backup you have never restored is a hope, not a backup. This step is mandatory before you trust the system with real data.

### Step 23: set the offsite remote

Configure `BACKUP_OFFSITE_REMOTE` (an rclone remote to Backblaze B2, another Hetzner box, or similar) in `.env`, restart the worker, and confirm the next run flips `offsite_synced` to true for the newest files.

## Part H: verification

### Step 24: health and metrics

Run: `curl https://YOUR_DOMAIN/api/v1/health/ready`

Expect 200 with postgres, redis, and an llm provider all ok.

### Step 25: end-to-end smoke

Log in through the browser at `https://YOUR_DOMAIN`, complete 2FA setup, send a chat message that creates a task, approve a file write, upload a document and get a cited answer. This exercises every subsystem through the production edge.

## Edge cases a weaker model would miss

1. **Do not touch ThemisIQ.** Different container names (the `odin-` prefix via compose project name `-p odin`), different host ports (5434 loopback DB, 8000 app, 6381 redis if published at all), a separate Postgres container and volume, a separate nginx server block. Never point ODIN at ThemisIQ's database.
2. **Set the compose project name** with `-p odin` or `name: odin` in the compose file, or the default folder-name project could clash with container names on a shared host.
3. **Publish Postgres and Redis on loopback only** (`127.0.0.1:5434:5432`) or not at all. A `0.0.0.0` bind on a public VPS exposes your database to the internet in minutes.
4. **`/metrics` must not be public.** Restrict it to localhost in the nginx block; it leaks internal timing and queue depth otherwise.
5. **WebSocket proxying needs the upgrade headers** (`Upgrade`, `Connection "upgrade"`, `proxy_read_timeout` raised); without them chat silently never streams in production while working perfectly in dev.
6. **`client_max_body_size 60m`** in nginx, or the 50 MB uploads die at nginx with a 413 before ever reaching FastAPI.
7. **Migrate before starting the app workers**, and start Postgres before migrating; `depends_on` does not guarantee readiness, hence the staged Steps 12 to 14.
8. **The restore test uses a scratch DB and drops it**; never restore over the live database to "test" it.
9. **inotify on the real Linux host works** (`WATCHER_FORCE_POLLING=0`); leaving polling on wastes CPU scanning the tree every few seconds forever.
10. **Certbot vs Cloudflare origin certs must match ThemisIQ's pattern.** Running certbot behind an orange-clouded Cloudflare proxy without DNS-01 can fail the HTTP-01 challenge; know which mode the existing site uses before Step 20.
11. **`secure` cookies require HTTPS end to end.** With Cloudflare in front, ensure SSL mode is Full (strict) so the origin is really HTTPS, or the SameSite=Strict+Secure refresh cookie is dropped and logins mysteriously fail only in production.
12. **Two-worker uvicorn shares no in-memory state.** The WhatsApp dedup set and breaker state become per-worker. For a single-user system two workers is fine, but pin `--workers 2` knowingly; if dedup misses appear, drop to one worker or move the dedup set to Redis (a documented follow-up, not a launch blocker).

## Acceptance criteria (verify each)

1. `docker ps` shows odin-prefixed containers running AND the ThemisIQ containers still running and healthy.
2. ThemisIQ's site still loads and functions (open it in a browser) after ODIN is up and nginx reloaded.
3. `curl https://YOUR_DOMAIN/api/v1/health/ready` returns 200 over real TLS.
4. `curl https://YOUR_DOMAIN/metrics` from OUTSIDE the box is refused/404; from the box (`curl http://127.0.0.1:8000/metrics`) it works.
5. Browser login over HTTPS works and survives a page reload (the Secure+Strict cookie is stored, proving end-to-end TLS).
6. A chat message streams token by token in production (WS upgrade proven).
7. `bash /opt/odin/scripts/restore_test.sh` prints PASS.
8. A 50 MB upload succeeds through nginx.
9. WhatsApp: a message to the business number gets a Hermes reply (after Part F).
10. The Postgres port is not reachable from another host: `nmap -p 5434 YOUR_DOMAIN` from your workstation shows it closed/filtered.

## Post-launch follow-ups (not launch blockers, record in DEPLOY.md)

1. Move the WhatsApp dedup set and LLM breaker state to Redis if running more than one uvicorn worker.
2. Add the 6-month WhatsApp DPIA review reminder (mirrors the ThemisIQ bridge governance gate) if ODIN is ever exposed beyond the single owner.
3. Consider a read replica or logical backup verification cadence if the knowledge base grows past a few GB.
