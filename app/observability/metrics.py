from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


OUTBOX_EVENT_STATUSES = ("pending", "processing", "processed", "failed")


HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests.",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "route", "status"],
)

SEARCH_REQUESTS_TOTAL = Counter(
    "search_requests_total",
    "Total number of ticket search requests.",
    ["status"],
)

SEARCH_UNAVAILABLE_TOTAL = Counter(
    "search_unavailable_total",
    "Total number of ticket search requests that failed because search was unavailable.",
)

SEARCH_REQUEST_DURATION_SECONDS = Histogram(
    "search_request_duration_seconds",
    "Ticket search request duration in seconds.",
    ["status"],
)

OUTBOX_EVENTS_BY_STATUS = Gauge(
    "outbox_events_by_status",
    "Current number of outbox events grouped by status.",
    ["status"],
)


def record_http_request(
    *,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    status = str(status_code)

    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        route=route,
        status=status,
    ).inc()

    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        route=route,
        status=status,
    ).observe(duration_seconds)


def record_search_request(
    *,
    status: str,
    duration_seconds: float,
) -> None:
    SEARCH_REQUESTS_TOTAL.labels(status=status).inc()
    SEARCH_REQUEST_DURATION_SECONDS.labels(status=status).observe(duration_seconds)


def record_search_unavailable() -> None:
    SEARCH_UNAVAILABLE_TOTAL.inc()


def update_outbox_events_by_status(counts_by_status: dict[str, int]) -> None:
    for status in OUTBOX_EVENT_STATUSES:
        OUTBOX_EVENTS_BY_STATUS.labels(status=status).set(
            counts_by_status.get(status, 0)
        )


def metrics_response() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )