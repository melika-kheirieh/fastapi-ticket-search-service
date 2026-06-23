import logging

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreateRequest, TicketUpdateRequest
from app.search.client import create_elasticsearch_client
from app.search.documents import ticket_to_search_document
from app.search.indexer import delete_ticket_document, index_ticket_document


logger = logging.getLogger(__name__)


class TicketService:
    def __init__(self, db: Session):
        self.repository = TicketRepository(db)
        self.db = db

    def create_ticket(self, payload: TicketCreateRequest) -> Ticket:
        ticket = Ticket(
            user_id=payload.user_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            category=payload.category,
            tags=payload.tags,
        )

        self.repository.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        try:
            client = create_elasticsearch_client()
            document = ticket_to_search_document(ticket)
            index_ticket_document(client, document)
        except Exception:
            logger.exception(
                "Failed to index ticket in Elasticsearch",
                extra={"ticket_id": ticket.id},
            )

        return ticket

    def list_tickets(
        self,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        user_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Ticket]:
        return self.repository.get_all(
            status=status,
            priority=priority,
            category=category,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        return self.repository.get_by_id(ticket_id)

    def update_ticket(
        self,
        ticket_id: int,
        payload: TicketUpdateRequest,
    ) -> Ticket | None:
        ticket = self.repository.get_by_id(ticket_id)

        if ticket is None:
            return None

        if payload.title is not None:
            ticket.title = payload.title

        if payload.description is not None:
            ticket.description = payload.description

        if payload.status is not None:
            ticket.status = payload.status

        if payload.priority is not None:
            ticket.priority = payload.priority

        if payload.category is not None:
            ticket.category = payload.category

        if payload.tags is not None:
            ticket.tags = payload.tags

        self.repository.update(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        try:
            client = create_elasticsearch_client()
            document = ticket_to_search_document(ticket)
            index_ticket_document(client, document)
        except Exception:
            logger.exception(
                "Failed to update ticket in Elasticsearch",
                extra={"ticket_id": ticket.id},
            )

        return ticket

    def delete_ticket(self, ticket_id: int) -> bool:
        ticket = self.repository.get_by_id(ticket_id)

        if ticket is None:
            return False

        ticket_id_to_delete = ticket.id

        self.repository.delete(ticket)
        self.db.commit()

        try:
            client = create_elasticsearch_client()
            delete_ticket_document(client, ticket_id_to_delete)
        except Exception:
            logger.exception(
                "Failed to delete ticket from Elasticsearch",
                extra={"ticket_id": ticket_id_to_delete},
            )

        return True