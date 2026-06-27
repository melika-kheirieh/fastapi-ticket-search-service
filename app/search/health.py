from fastapi import Depends
from fastapi.responses import JSONResponse


def get_search_subsystem_status(search_client) -> dict:
    try:
        is_available = search_client.ping()
    except Exception as exc:
        return {
            "status": "unavailable",
            "reason": "elasticsearch_ping_failed",
            "error": exc.__class__.__name__,
        }

    if not is_available:
        return {
            "status": "unavailable",
            "reason": "elasticsearch_ping_returned_false",
        }

    return {
        "status": "ok",
    }