import pytest

from app.models.outbox_event import OutboxEvent
from app.models.ticket import Ticket
from app.repositories.outbox_event_repository import OutboxEventRepository
from app.schemas.ticket import TicketCreateRequest, TicketUpdateRequest
from app.services.ticket_service import TicketService


def add_ticket(db_session) -> Ticket:
    ticket = Ticket(
        user_id=7,
        title="Payment failed",
        description="Payment was not captured",
        status="open",
        priority="high",
        category="billing",
        tags=["payment", "checkout"],
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


def test_create_ticket_persists_ticket_and_outbox_event(db_session):
    service = TicketService(db_session)

    ticket = service.create_ticket(
        TicketCreateRequest(
            user_id=7,
            title="Payment failed",
            description="Payment was not captured",
            status="open",
            priority="high",
            category="billing",
            tags=["payment", "checkout"],
        )
    )

    persisted_ticket = db_session.get(Ticket, ticket.id)
    events = db_session.query(OutboxEvent).all()

    assert persisted_ticket is not None
    assert persisted_ticket.title == "Payment failed"

    assert len(events) == 1
    assert events[0].aggregate_type == "ticket"
    assert events[0].aggregate_id == ticket.id
    assert events[0].event_type == "ticket.created"
    assert events[0].status == "pending"


def test_create_ticket_rolls_back_when_outbox_event_fails(db_session, monkeypatch):
    def fake_add_event(self, **kwargs):
        raise RuntimeError("outbox failed")

    monkeypatch.setattr(
        OutboxEventRepository,
        "add_event",
        fake_add_event,
    )

    service = TicketService(db_session)

    with pytest.raises(RuntimeError, match="outbox failed"):
        service.create_ticket(
            TicketCreateRequest(
                user_id=7,
                title="Payment failed",
                description="Payment was not captured",
                status="open",
                priority="high",
                category="billing",
                tags=["payment", "checkout"],
            )
        )

    tickets = db_session.query(Ticket).all()
    events = db_session.query(OutboxEvent).all()

    assert tickets == []
    assert events == []


def test_update_ticket_records_outbox_event(db_session):
    ticket = add_ticket(db_session)

    service = TicketService(db_session)

    updated_ticket = service.update_ticket(
        ticket.id,
        TicketUpdateRequest(status="closed"),
    )

    events = db_session.query(OutboxEvent).all()

    assert updated_ticket is not None
    assert updated_ticket.status == "closed"

    assert len(events) == 1
    assert events[0].aggregate_type == "ticket"
    assert events[0].aggregate_id == ticket.id
    assert events[0].event_type == "ticket.updated"
    assert events[0].status == "pending"


def test_update_ticket_creates_sequential_outbox_events(db_session):
    service = TicketService(db_session)

    ticket = service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Old title",
            description="Old description",
            status="open",
            priority="medium",
            category="billing",
            tags=["invoice"],
        )
    )

    updated_ticket = service.update_ticket(
        ticket.id,
        TicketUpdateRequest(title="New title"),
    )

    events = (
        db_session.query(OutboxEvent)
        .order_by(OutboxEvent.id)
        .all()
    )

    assert updated_ticket is not None
    assert updated_ticket.title == "New title"
    assert len(events) == 2
    assert events[1].aggregate_type == "ticket"
    assert events[1].aggregate_id == ticket.id
    assert events[1].event_type == "ticket.updated"
    assert events[1].status == "pending"


def test_update_ticket_returns_none_when_ticket_does_not_exist(db_session):
    service = TicketService(db_session)

    result = service.update_ticket(
        999,
        TicketUpdateRequest(status="closed"),
    )

    events = db_session.query(OutboxEvent).all()

    assert result is None
    assert events == []


def test_delete_ticket_records_outbox_event(db_session):
    ticket = add_ticket(db_session)
    ticket_id = ticket.id

    service = TicketService(db_session)

    deleted = service.delete_ticket(ticket_id)

    persisted_ticket = db_session.get(Ticket, ticket_id)
    events = db_session.query(OutboxEvent).all()

    assert deleted is True
    assert persisted_ticket is None

    assert len(events) == 1
    assert events[0].aggregate_type == "ticket"
    assert events[0].aggregate_id == ticket_id
    assert events[0].event_type == "ticket.deleted"
    assert events[0].status == "pending"


def test_delete_ticket_creates_sequential_outbox_events(db_session):
    service = TicketService(db_session)

    ticket = service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Delete me",
            description="This ticket should be deleted.",
            status="open",
            priority="low",
            category="general",
            tags=["cleanup"],
        )
    )

    ticket_id = ticket.id

    result = service.delete_ticket(ticket_id)

    events = (
        db_session.query(OutboxEvent)
        .order_by(OutboxEvent.id)
        .all()
    )

    deleted_ticket = db_session.get(Ticket, ticket_id)

    assert result is True
    assert deleted_ticket is None
    assert len(events) == 2
    assert events[1].aggregate_type == "ticket"
    assert events[1].aggregate_id == ticket_id
    assert events[1].event_type == "ticket.deleted"
    assert events[1].status == "pending"


def test_delete_ticket_returns_false_when_ticket_does_not_exist(db_session):
    service = TicketService(db_session)

    deleted = service.delete_ticket(999)

    events = db_session.query(OutboxEvent).all()

    assert deleted is False
    assert events == []
