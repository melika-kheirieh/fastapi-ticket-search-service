from typing import Any

from sqlalchemy.orm import Session

from app.repositories.outbox_event_repository import OutboxEventRepository
from app.repositories.ticket_repository import TicketRepository


class UnitOfWork:
    def __init__(self, db: Session):
        self.db = db
        self.tickets = TicketRepository(db)
        self.outbox_events = OutboxEventRepository(db)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: Any) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()