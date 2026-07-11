#!/usr/bin/env bash
# Restore the newest backup into a scratch database and verify it.
# Run: bash /opt/odin/scripts/restore_test.sh
# Requires: pg_restore, psql, access to the ODIN database-node container

set -e

SCRATCH_DB="odin_restore_test_$$"
BACKUP_DIR="/opt/odin/backups"
COMPOSE_FILE="/opt/odin/docker-compose.prod.yml"
DB_SERVICE="database-node"

# Load DB credentials from .env
set -a
source /opt/odin/.env
set +a

# Find the newest dump
DUMP=$(ls -t "$BACKUP_DIR"/odin_*.dump 2>/dev/null | head -1)
if [ -z "$DUMP" ]; then
  echo "FAIL: no dump files found in $BACKUP_DIR"
  exit 1
fi
echo "Testing restore of: $DUMP"

# Create scratch database
docker compose -p odin -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -c "CREATE DATABASE $SCRATCH_DB;"

# Restore into scratch
docker compose -p odin -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  sh -c "PGPASSWORD=$DB_PASSWORD pg_restore -U $DB_USER -d $SCRATCH_DB /backups/$(basename $DUMP)" || true

# Copy the dump into the container first (pg_restore reads from local path)
# Instead: stream via docker cp approach - mount backups dir is already in compose
# The celery-worker volume mounts /opt/odin/backups:/backups, reuse that container
docker cp "$DUMP" "$(docker compose -p odin -f "$COMPOSE_FILE" ps -q "$DB_SERVICE")":/tmp/restore_test.dump

docker compose -p odin -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  sh -c "PGPASSWORD=$DB_PASSWORD pg_restore -U $DB_USER -d $SCRATCH_DB /tmp/restore_test.dump"

# Count tables
TABLE_COUNT=$(docker compose -p odin -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d "$SCRATCH_DB" -t -c \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

TABLE_COUNT=$(echo "$TABLE_COUNT" | tr -d ' ')

echo "Table count in restored DB: $TABLE_COUNT"

# Drop scratch database
docker compose -p odin -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -c "DROP DATABASE $SCRATCH_DB;"

if [ "$TABLE_COUNT" -ge 19 ]; then
  echo "PASS: restore succeeded, $TABLE_COUNT tables found"
  exit 0
else
  echo "FAIL: expected at least 19 tables, found $TABLE_COUNT"
  exit 1
fi
