from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.config import settings
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routers.activity import router as activity_router
from app.routers.approvals import router as approvals_router
from app.routers.auth import router as auth_router
from app.routers.auth import ws_router as auth_ws_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.conversations import search_router
from app.routers.dashboard import router as dashboard_router
from app.routers.files import router as files_router
from app.routers.health import router as health_router
from app.routers.kb import router as kb_router
from app.routers.notifications import router as notifications_router
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router
from app.routers.tasks import subtask_router
from app.routers.ws import router as ws_router

configure_logging()

app = FastAPI(title="ODIN Gateway", version="0.1.0", docs_url="/api/docs", redoc_url=None)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(auth_ws_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(subtask_router)
app.include_router(conversations_router)
app.include_router(search_router)
app.include_router(notifications_router)
app.include_router(activity_router)
app.include_router(dashboard_router)
app.include_router(ws_router)
app.include_router(chat_router)
app.include_router(approvals_router)
app.include_router(files_router)
app.include_router(kb_router)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
