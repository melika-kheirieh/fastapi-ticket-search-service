from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreateRequest, TicketUpdateRequest


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

        return ticket

    def delete_ticket(self, ticket_id: int) -> bool:
        ticket = self.repository.get_by_id(ticket_id)

        if ticket is None:
            return False

        self.repository.delete(ticket)
        self.db.commit()

        return True