from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.db import async_session

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live():
    return {"status": "alive"}


@router.get("/health/ready")
async def ready():
    checks: dict = {}
    status_code = 200

    # Postgres check
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        status_code = 503

    # Redis check
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        status_code = 503

    # LLM provider key presence
    checks["llm_providers"] = {
        "deepseek": "configured" if settings.DEEPSEEK_API_KEY else "missing_key",
        "anthropic": "configured" if settings.ANTHROPIC_API_KEY else "missing_key",
        "gemini": "configured" if settings.GEMINI_API_KEY else "missing_key",
        "openai": "configured" if settings.OPENAI_API_KEY else "missing_key",
        "ollama": "configured",
    }

    from fastapi.responses import JSONResponse
    return JSONResponse(content={"status": "ready" if status_code == 200 else "degraded", **checks}, status_code=status_code)
