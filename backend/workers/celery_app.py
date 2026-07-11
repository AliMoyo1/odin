from celery import Celery
from celery.schedules import crontab

from app.config import settings

app = Celery(
    "odin",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.indexing",
        "workers.memory_jobs",
        "workers.backup_jobs",
        "workers.agenda_jobs",
        "workers.infra_jobs",
        "workers.maintenance_jobs",
    ],
)

app.conf.update(
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Backups (02:00 daily)
        "backup-database-daily": {
            "task": "backup_database",
            "schedule": crontab(hour=2, minute=0),
        },
        # Morning agenda (08:00 daily)
        "morning-agenda-daily": {
            "task": "morning_agenda",
            "schedule": crontab(hour=8, minute=0),
        },
        # Infra audit (01:00 Monday)
        "infra-audit-weekly": {
            "task": "infra_audit",
            "schedule": crontab(hour=1, minute=0, day_of_week=1),
        },
        # Stale task cleanup (03:00 daily)
        "stale-task-cleanup-daily": {
            "task": "stale_task_cleanup",
            "schedule": crontab(hour=3, minute=0),
        },
        # Memory consolidation (04:00 Sunday)
        "memory-consolidation-weekly": {
            "task": "consolidate_memories",
            "schedule": crontab(hour=4, minute=0, day_of_week=0),
        },
        # Conversation summarize (04:30 Sunday)
        "conversation-summarize-weekly": {
            "task": "summarize_conversations",
            "schedule": crontab(hour=4, minute=30, day_of_week=0),
        },
        # Knowledge reindex (05:00 daily)
        "knowledge-reindex-daily": {
            "task": "knowledge_reindex",
            "schedule": crontab(hour=5, minute=0),
        },
        # SSL cert countdown (06:00 on 1st of month)
        "ssl-cert-countdown-monthly": {
            "task": "ssl_cert_countdown",
            "schedule": crontab(hour=6, minute=0, day_of_month=1),
        },
        # WS ticket cleanup (23:00 daily)
        "ws-ticket-cleanup-daily": {
            "task": "ws_ticket_cleanup",
            "schedule": crontab(hour=23, minute=0),
        },
    },
)


@app.task(name="ping")
def ping() -> str:
    return "pong"
