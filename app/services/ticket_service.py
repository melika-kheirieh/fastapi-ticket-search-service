from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreateRequest


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
        limit: int = 20,
        offset: int = 0,
    ) -> list[Ticket]:
        return self.repository.get_all(
            status=status,
            priority=priority,
            category=category,
            limit=limit,
            offset=offset,
        )

    def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        return self.repository.get_by_id(ticket_id)
