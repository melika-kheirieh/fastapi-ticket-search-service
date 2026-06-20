from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreateRequest


class TicketService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TicketRepository(db)

    def create_ticket(self, payload: TicketCreateRequest) -> Ticket:
        ticket = Ticket(
            user_id=payload.user_id,
            title=payload.title,
            description=payload.description,
            status=payload.status.value,
            priority=payload.priority.value,
            category=payload.category,
            tags=payload.tags,
        )

        try:
            created_ticket = self.repository.add(ticket)
            self.db.commit()
            self.db.refresh(created_ticket)
            return created_ticket
        except Exception:
            self.db.rollback()
            raise
