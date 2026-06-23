from elasticsearch import Elasticsearch

from app.core.config import settings
from app.search.mappings import TICKET_INDEX_MAPPING


def create_elasticsearch_client() -> Elasticsearch:
    return Elasticsearch(settings.elasticsearch_url)


def create_ticket_index_if_missing(
    client: Elasticsearch,
    index_name: str | None = None,
) -> bool:
    resolved_index_name = index_name or settings.ticket_search_index

    if client.indices.exists(index=resolved_index_name):
        return False

    client.indices.create(
        index=resolved_index_name,
        settings=TICKET_INDEX_MAPPING["settings"],
        mappings=TICKET_INDEX_MAPPING["mappings"],
    )
    return True