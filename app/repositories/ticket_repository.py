from sqlalchemy import select
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
        user_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Ticket]:
        stmt = select(Ticket)

        if status is not None:
            stmt = stmt.where(Ticket.status == status)

        if priority is not None:
            stmt = stmt.where(Ticket.priority == priority)

        if category is not None:
            stmt = stmt.where(Ticket.category == category)

        if user_id is not None:
            stmt = stmt.where(Ticket.user_id == user_id)

        stmt = stmt.order_by(
            Ticket.created_at.desc(),
            Ticket.id.desc(),
        )
        stmt = stmt.limit(limit).offset(offset)

        result = self.db.execute(stmt)

        return list(result.scalars().all())

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        return self.db.get(Ticket, ticket_id)

    def update(self, ticket: Ticket) -> Ticket:
        self.db.flush()

        return ticket

    def delete(self, ticket: Ticket) -> None:
        self.db.delete(ticket)
        self.db.flush()