from prometheus_client import Counter, Gauge, Histogram

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "method", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["path"],
)

ws_connections_active = Gauge(
    "ws_connections_active",
    "Active WebSocket connections",
)

llm_calls_total = Counter(
    "llm_calls_total",
    "Total LLM provider calls",
    ["provider", "outcome"],
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM call duration to first token",
    ["provider"],
)

celery_queue_depth = Gauge(
    "celery_queue_depth",
    "Celery task queue depth",
)
