from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.search.client import recreate_ticket_index
from app.search.documents import ticket_to_search_document
from app.search.indexer import index_ticket_document
from app.core.config import settings
from app.search.client import create_elasticsearch_client, recreate_ticket_index


if TYPE_CHECKING:
    from elasticsearch import Elasticsearch


def reindex_tickets(
    db: Session,
    client: "Elasticsearch",
    index_name: str | None = None,
) -> int:
    recreate_ticket_index(client, index_name=index_name)

    tickets = db.execute(
        select(Ticket).order_by(Ticket.id.asc())
    ).scalars()

    count = 0

    for ticket in tickets:
        document = ticket_to_search_document(ticket)

        index_ticket_document(
            client=client,
            document=document,
            index_name=index_name,
        )

        count += 1

    return count


def main() -> None:
    from app.db.session import SessionLocal

    client = create_elasticsearch_client()
    db = SessionLocal()

    try:
        count = reindex_tickets(
            db=db,
            client=client,
            index_name=settings.ticket_search_index,
        )
    finally:
        db.close()

    print(f"Reindexed {count} tickets into {settings.ticket_search_index}")


if __name__ == "__main__":
    main()