import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.outbox_event import OutboxEvent
from app.models.ticket import Ticket
from app.repositories.outbox_event_repository import OutboxEventRepository
from app.schemas.ticket import TicketCreateRequest, TicketUpdateRequest
from app.services.ticket_service import TicketService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_create_ticket_creates_outbox_event(db_session):
    service = TicketService(db_session)

    ticket = service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Cannot login",
            description="Login fails with invalid session.",
            status="open",
            priority="high",
            category="auth",
            tags=["login", "session"],
        )
    )

    events = db_session.query(OutboxEvent).all()

    assert len(events) == 1
    assert events[0].aggregate_type == "ticket"
    assert events[0].aggregate_id == ticket.id
    assert events[0].event_type == "ticket.created"
    assert events[0].status == "pending"


def test_update_ticket_creates_outbox_event(db_session):
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


def test_update_missing_ticket_does_not_create_outbox_event(db_session):
    service = TicketService(db_session)

    result = service.update_ticket(
        999,
        TicketUpdateRequest(title="Does not matter"),
    )

    events = db_session.query(OutboxEvent).all()

    assert result is None
    assert events == []


def test_delete_ticket_creates_outbox_event(db_session):
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


def test_delete_missing_ticket_does_not_create_outbox_event(db_session):
    service = TicketService(db_session)

    result = service.delete_ticket(999)

    events = db_session.query(OutboxEvent).all()

    assert result is False
    assert events == []


def test_create_ticket_rolls_back_when_outbox_event_creation_fails(
    db_session,
    monkeypatch,
):
    def fail_add_event(*args, **kwargs):
        raise RuntimeError("outbox failed")

    monkeypatch.setattr(
        OutboxEventRepository,
        "add_event",
        fail_add_event,
    )

    service = TicketService(db_session)

    with pytest.raises(RuntimeError, match="outbox failed"):
        service.create_ticket(
            TicketCreateRequest(
                user_id=1,
                title="Should rollback",
                description="This ticket should not be persisted.",
                status="open",
                priority="high",
                category="auth",
                tags=["rollback"],
            )
        )

    tickets = db_session.query(Ticket).all()
    events = db_session.query(OutboxEvent).all()

    assert tickets == []
    assert events == []