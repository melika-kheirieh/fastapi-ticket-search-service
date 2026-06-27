from sqlalchemy.orm import Session

from app.db.unit_of_work import UnitOfWork
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreateRequest, TicketUpdateRequest


class TicketService:
    def __init__(self, db: Session):
        self.uow = UnitOfWork(db)

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

        try:
            self.uow.tickets.add(ticket)

            self.uow.outbox_events.add_event(
                aggregate_type="ticket",
                aggregate_id=ticket.id,
                event_type="ticket.created",
                payload={},
            )

            self.uow.commit()
            self.uow.refresh(ticket)

            return ticket

        except Exception:
            self.uow.rollback()
            raise

    def list_tickets(
        self,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        user_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Ticket]:
        return self.uow.tickets.get_all(
            status=status,
            priority=priority,
            category=category,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        return self.uow.tickets.get_by_id(ticket_id)

    def update_ticket(
        self,
        ticket_id: int,
        payload: TicketUpdateRequest,
    ) -> Ticket | None:
        ticket = self.uow.tickets.get_by_id(ticket_id)

        if ticket is None:
            return None

        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(ticket, field, value)

        try:
            self.uow.tickets.update(ticket)

            self.uow.outbox_events.add_event(
                aggregate_type="ticket",
                aggregate_id=ticket.id,
                event_type="ticket.updated",
                payload={},
            )

            self.uow.commit()
            self.uow.refresh(ticket)

            return ticket

        except Exception:
            self.uow.rollback()
            raise

    def delete_ticket(self, ticket_id: int) -> bool:
        ticket = self.uow.tickets.get_by_id(ticket_id)

        if ticket is None:
            return False

        ticket_id_to_delete = ticket.id

        try:
            self.uow.tickets.delete(ticket)

            self.uow.outbox_events.add_event(
                aggregate_type="ticket",
                aggregate_id=ticket_id_to_delete,
                event_type="ticket.deleted",
                payload={},
            )

            self.uow.commit()

            return True

        except Exception:
            self.uow.rollback()
            raise