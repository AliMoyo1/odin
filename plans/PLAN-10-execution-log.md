# PLAN-10 Execution Log

## Status: IN PROGRESS

## Steps

- [x] Production Dockerfile (backend/Dockerfile)
- [x] docker-compose.prod.yml
- [x] nginx/odin.conf
- [x] scripts/restore_test.sh
- [x] DEPLOY.md
- [ ] Commit and push
- [ ] VPS: clone repo, create dirs
- [ ] VPS: fill .env with real secrets
- [ ] VPS: generate JWT keypair
- [ ] VPS: build images
- [ ] VPS: run migrations
- [ ] VPS: start all services
- [ ] VPS: create admin user
- [ ] Build and copy frontend dist to VPS
- [ ] VPS: install nginx config, test, reload
- [ ] VPS: issue TLS certificate
- [ ] VPS: health check passes
- [ ] VPS: restore test passes (PASS)
- [ ] WhatsApp go-live

## Changes made

- Created backend/Dockerfile: production image, uvicorn --workers 2, no --reload
- Created docker-compose.prod.yml: name=odin, loopback binds, named volume odin_prod_db, no source mounts, restart: unless-stopped
- Created nginx/odin.conf: TLS, WS upgrade, /metrics localhost-only, CSP/HSTS/X-Frame-Options headers, client_max_body_size 60m
- Created scripts/restore_test.sh: restore newest dump to scratch DB, count tables, print PASS/FAIL
- Created DEPLOY.md: step-by-step runbook, one command per step
