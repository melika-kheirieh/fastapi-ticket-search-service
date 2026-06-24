from app.core.config import settings
from app.search.client import (
    create_elasticsearch_client,
    create_ticket_index_if_missing,
)


def main() -> None:
    client = create_elasticsearch_client()
    created = create_ticket_index_if_missing(client)

    if created:
        print(f"Created Elasticsearch index: {settings.ticket_search_index}")
        return

    print(f"Elasticsearch index already exists: {settings.ticket_search_index}")


if __name__ == "__main__":
    main()