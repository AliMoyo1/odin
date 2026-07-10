from celery import Celery

from app.config import settings

app = Celery("odin", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

app.conf.update(
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={},
)


@app.task(name="ping")
def ping() -> str:
    return "pong"
