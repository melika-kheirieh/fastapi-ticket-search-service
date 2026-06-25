from datetime import datetime
from typing import Any

from elasticsearch import Elasticsearch
from elastic_transport import (
    ApiError,
    ConnectionError,
    ConnectionTimeout,
    SerializationError,
    TransportError,
)

from app.core.config import settings
from app.search.exceptions import SearchUnavailableError


def _is_elasticsearch_exception(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            ApiError,
            ConnectionError,
            ConnectionTimeout,
            SerializationError,
            TransportError,
        ),
    )


def build_ticket_search_query(
    query: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    user_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> dict[str, Any]:
    filters = []

    if status is not None:
        filters.append({"term": {"status": status}})

    if priority is not None:
        filters.append({"term": {"priority": priority}})

    if category is not None:
        filters.append({"term": {"category": category}})

    if tag is not None:
        filters.append({"term": {"tags": tag}})

    if user_id is not None:
        filters.append({"term": {"user_id": user_id}})

    created_at_range = {}

    if created_from is not None:
        created_at_range["gte"] = created_from.isoformat()

    if created_to is not None:
        created_at_range["lte"] = created_to.isoformat()

    if created_at_range:
        filters.append({"range": {"created_at": created_at_range}})

    if query is None:
        must = [{"match_all": {}}]
    else:
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "description"],
                }
            }
        ]

    return {
        "bool": {
            "must": must,
            "filter": filters,
        }
    }


def build_ticket_search_body(
    query: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    user_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    return {
        "query": build_ticket_search_query(
            query=query,
            status=status,
            priority=priority,
            category=category,
            tag=tag,
            user_id=user_id,
            created_from=created_from,
            created_to=created_to,
        ),
        "from": offset,
        "size": limit,
        "sort": [
            {"created_at": {"order": "desc"}},
            {"id": {"order": "desc"}},
        ],
    }


def search_tickets(
    client: Elasticsearch,
    query: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    user_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
    index_name: str | None = None,
) -> list[dict[str, Any]]:
    resolved_index_name = index_name or settings.ticket_search_index

    try:
        response = client.search(
            index=resolved_index_name,
            body=build_ticket_search_body(
                query=query,
                status=status,
                priority=priority,
                category=category,
                tag=tag,
                user_id=user_id,
                created_from=created_from,
                created_to=created_to,
                limit=limit,
                offset=offset,
            ),
        )
    except Exception as exc:
        if _is_elasticsearch_exception(exc):
            raise SearchUnavailableError("Search backend is unavailable") from exc
        raise

    return [hit["_source"] for hit in response["hits"]["hits"]]