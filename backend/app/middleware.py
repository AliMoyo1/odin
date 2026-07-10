import time
import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import http_request_duration_seconds, http_requests_total

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = structlog.get_logger(service="http")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(req_id)
        structlog.contextvars.bind_contextvars(request_id=req_id)

        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start
        duration_ms = round(elapsed * 1000, 1)

        path = request.url.path
        http_requests_total.labels(path=path, method=request.method, status=response.status_code).inc()
        http_request_duration_seconds.labels(path=path).observe(elapsed)

        response.headers["X-Request-ID"] = req_id
        logger.info(
            "request",
            method=request.method,
            path=path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        structlog.contextvars.clear_contextvars()
        return response
