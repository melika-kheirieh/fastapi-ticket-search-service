from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


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


def metrics_response() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )