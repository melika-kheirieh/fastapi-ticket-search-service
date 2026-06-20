from sqlalchemy.orm import Session
from app.models.ticket import Ticket


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def get_all(
        self,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Ticket]:
        query = self.db.query(Ticket)

        if status:
            query = query.filter(Ticket.status == status)

        if priority:
            query = query.filter(Ticket.priority == priority)

        if category:
            query = query.filter(Ticket.category == category)

        return query.offset(offset).limit(limit).all()

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
