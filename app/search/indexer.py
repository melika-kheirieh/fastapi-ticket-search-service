from typing import Any

from elasticsearch import Elasticsearch

from app.core.config import settings


def index_ticket_document(
    client: Elasticsearch,
    document: dict[str, Any],
    index_name: str | None = None,
) -> None:
    resolved_index_name = index_name or settings.ticket_search_index

    client.index(
        index=resolved_index_name,
        id=str(document["id"]),
        document=document,
    )


def delete_ticket_document(
    client: Elasticsearch,
    ticket_id: int,
    index_name: str | None = None,
) -> None:
    resolved_index_name = index_name or settings.ticket_search_index

    client.options(ignore_status=[404]).delete(
        index=resolved_index_name,
        id=str(ticket_id),
    )