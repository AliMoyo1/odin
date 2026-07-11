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
    ],
)

app.conf.update(
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "consolidate-memories-daily": {
            "task": "consolidate_memories",
            "schedule": crontab(hour=3, minute=0),
        },
        "summarize-conversations-every-2h": {
            "task": "summarize_conversations",
            "schedule": crontab(minute=0, hour="*/2"),
        },
    },
)


@app.task(name="ping")
def ping() -> str:
    return "pong"
