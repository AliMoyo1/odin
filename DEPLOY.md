# ODIN Deployment Runbook

Production target: Hetzner VPS alongside ThemisIQ. One command per step.
Never join two commands with &&. Never type a pipe character in the console.

## Before you start

Check ThemisIQ containers are still healthy: `docker ps`
Confirm the VPS public IP and your domain (referred to as YOUR_DOMAIN below).

---

## Part A: coexistence check

**Step 1.** Confirm running containers and ports:
`docker ps --format "table {{.Names}}\t{{.Ports}}"`

ThemisIQ uses port 80/443 via the host nginx and its own Postgres.
ODIN will use: app 127.0.0.1:8000, DB 127.0.0.1:5434, Redis internal only.
Container names are prefixed `odin-` (set by `name: odin` in compose file).

**Step 2.** Confirm nginx is the host reverse proxy:
`systemctl status nginx`

---

## Part B: DNS

**Step 3.** In Cloudflare, add an A record: `odin` pointing to the VPS IP.
Match the proxy mode (orange or grey cloud) that ThemisIQ uses.

**Step 4.** Set YOUR_DOMAIN (example: odin.themisiq.net).
Replace every occurrence of YOUR_DOMAIN in `nginx/odin.conf` with the real hostname.

---

## Part C: get the code onto the VPS

**Step 5.** Clone the repo:
`git clone https://github.com/AliMoyo1/odin.git /opt/odin`

**Step 6.** Create directories:
`mkdir -p /opt/odin/keys /opt/odin/workspace /opt/odin/backups /opt/odin/frontend/dist`

---

## Part D: secrets

**Step 7.** Copy the example env:
`cp /opt/odin/.env.example /opt/odin/.env`

**Step 8.** Generate SECRET_KEY on the workstation and paste into .env:
`python -c "import secrets; print(secrets.token_hex(32))"`

**Step 9.** Generate ENCRYPTION_KEY on the workstation and paste into .env:
`python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"`

**Step 10.** Edit .env with real values:
`nano /opt/odin/.env`

Required values to fill:
- ENVIRONMENT=prod
- SECRET_KEY (from Step 8)
- ENCRYPTION_KEY (from Step 9)
- DB_USER, DB_PASSWORD, DB_NAME, DATABASE_URL (pointing at database-node:5432)
- CORS_ALLOWED_ORIGIN=https://YOUR_DOMAIN
- LLM keys: DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, etc.
- WA_DRY_RUN=1 (keep off until TLS is confirmed)
- BACKUP_LOCAL_DIR=/backups
- BACKUP_RETENTION_DAYS=30

---

## Part E: JWT keypair

**Step 11.** Generate the JWT keypair inside a throwaway container:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml run --rm gateway-api python scripts/generate_keys.py /keys`

Confirm files exist: `ls -la /opt/odin/keys/`
Expected: jwt_private.pem (mode 600), jwt_public.pem

---

## Part F: build and bring up

**Step 12.** Build images:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml build`

**Step 13.** Start DB and Redis first:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml up -d database-node redis-broker`

**Step 14.** Run migrations:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml run --rm gateway-api alembic upgrade head`

**Step 15.** Start all services:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml up -d`

**Step 16.** Create the admin user:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml exec gateway-api python scripts/create_user.py --email alimoyo58@gmail.com --name Ali --password A_STRONG_PASSWORD`

---

## Part G: build and deploy the frontend

**Step 17.** On the workstation, in the frontend directory, build:
`npm run build`

**Step 18.** Copy the dist folder to the VPS (run on workstation):
`scp -r frontend/dist root@VPS_IP:/opt/odin/frontend/dist`

---

## Part H: nginx and TLS

**Step 19.** Copy the nginx server block:
`cp /opt/odin/nginx/odin.conf /etc/nginx/sites-available/odin.conf`

Open it with nano and replace YOUR_DOMAIN with the real domain:
`nano /etc/nginx/sites-available/odin.conf`

**Step 20.** Enable the site:
`ln -s /etc/nginx/sites-available/odin.conf /etc/nginx/sites-enabled/odin.conf`

**Step 21.** Test nginx config:
`nginx -t`

**Step 22.** Reload nginx:
`systemctl reload nginx`

**Step 23.** Issue TLS certificate (if using certbot to match ThemisIQ):
`certbot --nginx -d YOUR_DOMAIN`

If ThemisIQ uses Cloudflare origin certs (Full strict mode), install those instead.
Do not run certbot behind an orange-clouded domain without DNS-01 challenge.

---

## Part I: health check

**Step 24.** Check the health endpoint:
`curl https://YOUR_DOMAIN/api/v1/health/ready`

Expect 200 with postgres, redis, and llm_provider all ok.

**Step 25.** Confirm metrics are blocked externally (run from your workstation):
`curl https://YOUR_DOMAIN/metrics`

Expect 403 or connection refused. From the VPS itself it should work:
`curl http://127.0.0.1:8000/metrics`

---

## Part J: backups and restore test

**Step 26.** Trigger the backup manually (or wait for the 02:00 UTC run):
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml exec celery-worker celery -A workers.celery_app call backup_database`

**Step 27.** Confirm the dump file exists:
`ls -la /opt/odin/backups`

**Step 28.** Run the restore test:
`bash /opt/odin/scripts/restore_test.sh`

Expect: PASS

**Step 29.** Configure offsite remote in .env (Backblaze B2 or similar):
`nano /opt/odin/.env`
Set BACKUP_OFFSITE_REMOTE to an rclone remote path (e.g. b2:odin-backups).

**Step 30.** Restart worker to pick up new env:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml restart celery-worker`

---

## Part K: WhatsApp go-live

Only after TLS is confirmed and the health check passes.

**Step 31.** Edit .env and fill WhatsApp values, set WA_DRY_RUN=0:
`nano /opt/odin/.env`

Required: WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN,
WHATSAPP_APP_SECRET, WHATSAPP_ALLOWED_NUMBER.

**Step 32.** Restart the stack:
`docker compose -p odin -f /opt/odin/docker-compose.prod.yml up -d`

**Step 33.** In the Meta Developer Console:
- Go to WhatsApp > Configuration
- Set the webhook URL to: https://YOUR_DOMAIN/webhooks/whatsapp
- Set the verify token to match WHATSAPP_VERIFY_TOKEN
- Click Verify and subscribe to the `messages` event

**Step 34.** Send a WhatsApp message to the business number and confirm a reply arrives.

---

## Post-launch follow-ups (not launch blockers)

1. Move the WA dedup set and LLM breaker state to Redis if running more than one uvicorn worker.
2. Add a 6-month DPIA review reminder if ODIN is ever exposed beyond the single owner.
3. Consider a read replica or logical backup verification cadence if the knowledge base grows past a few GB.

---

## Acceptance checklist

- [ ] `docker ps` shows odin-prefixed containers running AND ThemisIQ still healthy
- [ ] ThemisIQ site still loads after nginx reload
- [ ] `curl https://YOUR_DOMAIN/api/v1/health/ready` returns 200
- [ ] Metrics endpoint is blocked externally
- [ ] Browser login over HTTPS survives a page reload
- [ ] Chat message streams token by token (WebSocket upgrade confirmed)
- [ ] `bash /opt/odin/scripts/restore_test.sh` prints PASS
- [ ] 50 MB upload succeeds through nginx
- [ ] WhatsApp message gets a Hermes reply
- [ ] `nmap -p 5434 YOUR_DOMAIN` shows port closed/filtered from outside
