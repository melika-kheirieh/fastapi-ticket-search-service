from typing import Any

from elasticsearch import Elasticsearch

from app.core.config import settings


def search_tickets(
    client: Elasticsearch,
    query: str,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    limit: int = 20,
    offset: int = 0,
    index_name: str | None = None,
) -> list[dict[str, Any]]:
    resolved_index_name = index_name or settings.ticket_search_index

    filters = []

    if status is not None:
        filters.append({"term": {"status": status}})

    if priority is not None:
        filters.append({"term": {"priority": priority}})

    if category is not None:
        filters.append({"term": {"category": category}})

    if tag is not None:
        filters.append({"term": {"tags": tag}})

    response = client.search(
        index=resolved_index_name,
        query={
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title", "description"],
                        }
                    }
                ],
                "filter": filters,
            }
        },
        from_=offset,
        size=limit,
    )

    return [hit["_source"] for hit in response["hits"]["hits"]]
