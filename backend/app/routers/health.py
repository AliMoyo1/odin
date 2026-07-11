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

    # LLM provider status (circuit breaker aware)
    from app.hermes import breaker as _breaker
    provider_status = {}
    for name in ["deepseek", "anthropic", "gemini", "openai", "ollama"]:
        configured = bool(getattr(settings, f"{name.upper()}_API_KEY", "")) or name == "ollama"
        if not configured:
            provider_status[name] = "missing_key"
        elif _breaker.get_state_snapshot(name)["circuit_open"]:
            provider_status[name] = "circuit_open"
        else:
            provider_status[name] = "available"
    checks["llm_provider"] = provider_status

    from fastapi.responses import JSONResponse
    return JSONResponse(content={"status": "ready" if status_code == 200 else "degraded", **checks}, status_code=status_code)
