import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.tickets import router as tickets_router
from app.core.config import settings
from app.core.request_context import reset_request_id, set_request_id
from app.core.logging import configure_logging
from app.search.dependencies import get_elasticsearch_client
from app.search.health import get_search_subsystem_status

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A PostgreSQL-backed ticket service with Elasticsearch search projection.",
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    token = set_request_id(request_id)
    started_at = time.perf_counter()

    logger.info(
        "Request started",
        extra={
            "event": "request_started",
            "method": request.method,
            "path": request.url.path,
        },
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "Request failed",
            extra={
                "event": "request_failed",
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise
    else:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "Request completed",
            extra={
                "event": "request_completed",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
    finally:
        reset_request_id(token)


@app.get("/health/search")
def search_health_check(search_client=Depends(get_elasticsearch_client)):
    status = get_search_subsystem_status(search_client)
    status_code = 200 if status["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=status)


app.include_router(tickets_router)