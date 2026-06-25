import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.outbox_event import OutboxEvent
from app.repositories.outbox_event_repository import OutboxEventRepository


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


def test_can_store_outbox_event(db_session):
    event = OutboxEvent(
        aggregate_type="ticket",
        aggregate_id=123,
        event_type="ticket.created",
    )

    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    saved_event = db_session.get(OutboxEvent, event.id)

    assert saved_event is not None
    assert saved_event.aggregate_type == "ticket"
    assert saved_event.aggregate_id == 123
    assert saved_event.event_type == "ticket.created"
    assert saved_event.status == "pending"
    assert saved_event.payload == {}
    assert saved_event.retry_count == 0
    assert saved_event.last_error is None
    assert saved_event.processed_at is None
    assert saved_event.created_at is not None
    assert saved_event.updated_at is not None


def test_outbox_event_repository_adds_event_without_committing(db_session):
    repository = OutboxEventRepository(db_session)

    event = repository.add_event(
        aggregate_type="ticket",
        aggregate_id=456,
        event_type="ticket.updated",
        payload={"source": "test"},
    )

    assert event.id is None
    assert event in db_session.new

    db_session.commit()
    db_session.refresh(event)

    saved_event = db_session.get(OutboxEvent, event.id)

    assert saved_event is not None
    assert saved_event.aggregate_type == "ticket"
    assert saved_event.aggregate_id == 456
    assert saved_event.event_type == "ticket.updated"
    assert saved_event.payload == {"source": "test"}
    assert saved_event.status == "pending"
    assert saved_event.retry_count == 0

def test_outbox_event_repository_gets_pending_events_in_order(db_session):
    repository = OutboxEventRepository(db_session)

    first = repository.add_event(
        aggregate_type="ticket",
        aggregate_id=1,
        event_type="ticket.created",
    )
    second = repository.add_event(
        aggregate_type="ticket",
        aggregate_id=2,
        event_type="ticket.created",
    )
    processed = repository.add_event(
        aggregate_type="ticket",
        aggregate_id=3,
        event_type="ticket.created",
    )

    db_session.commit()

    repository.mark_processed(processed)
    db_session.commit()

    pending_events = repository.get_pending_events(limit=10)

    assert [event.id for event in pending_events] == [first.id, second.id]


def test_outbox_event_repository_marks_event_processing(db_session):
    repository = OutboxEventRepository(db_session)

    event = repository.add_event(
        aggregate_type="ticket",
        aggregate_id=123,
        event_type="ticket.created",
    )
    db_session.commit()

    repository.mark_processing(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.status == "processing"


def test_outbox_event_repository_marks_event_processed(db_session):
    repository = OutboxEventRepository(db_session)

    event = repository.add_event(
        aggregate_type="ticket",
        aggregate_id=123,
        event_type="ticket.created",
    )
    db_session.commit()

    repository.mark_processed(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.status == "processed"
    assert event.processed_at is not None
    assert event.last_error is None


def test_outbox_event_repository_marks_event_failed(db_session):
    repository = OutboxEventRepository(db_session)

    event = repository.add_event(
        aggregate_type="ticket",
        aggregate_id=123,
        event_type="ticket.created",
    )
    db_session.commit()

    repository.mark_failed(event, error=RuntimeError("Elasticsearch is down"))
    db_session.commit()
    db_session.refresh(event)

    assert event.status == "failed"
    assert event.retry_count == 1
    assert event.last_error == "Elasticsearch is down"
    assert event.processed_at is None