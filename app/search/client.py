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


def recreate_ticket_index(
    client: "Elasticsearch",
    index_name: str | None = None,
) -> None:
    from app.search.mappings import TICKET_INDEX_MAPPING

    if index_name is None:
        from app.core.config import settings

        index_name = settings.ticket_search_index

    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)

    client.indices.create(
        index=index_name,
        mappings=TICKET_INDEX_MAPPING["mappings"],
        settings=TICKET_INDEX_MAPPING["settings"],
    )