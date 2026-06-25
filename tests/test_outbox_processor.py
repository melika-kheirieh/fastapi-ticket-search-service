from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.outbox_event import OutboxEvent
from app.outbox.processor import OutboxProcessor
from app.repositories.outbox_event_repository import OutboxEventRepository
from app.schemas.ticket import TicketCreateRequest
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

def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

class FakeSearchClient:
    pass


def test_processor_indexes_created_ticket_event(db_session, monkeypatch):
    indexed_documents = []

    def fake_ticket_to_search_document(ticket):
        return {
            "id": ticket.id,
            "title": ticket.title,
        }

    def fake_index_ticket_document(client, document):
        indexed_documents.append(document)

    monkeypatch.setattr(
        "app.outbox.processor.ticket_to_search_document",
        fake_ticket_to_search_document,
    )
    monkeypatch.setattr(
        "app.outbox.processor.index_ticket_document",
        fake_index_ticket_document,
    )

    service = TicketService(db_session)
    ticket = service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Cannot login",
            description="Login fails.",
            status="open",
            priority="high",
            category="auth",
            tags=["login"],
        )
    )

    processor = OutboxProcessor(
        db=db_session,
        search_client=FakeSearchClient(),
    )

    result = processor.process_events(limit=10)

    event = db_session.query(OutboxEvent).one()

    assert result.processed == 1
    assert result.failed == 0
    assert indexed_documents == [
        {
            "id": ticket.id,
            "title": "Cannot login",
        }
    ]
    assert event.status == "processed"
    assert event.processed_at is not None
    assert event.last_error is None


def test_processor_deletes_ticket_document_for_deleted_event(db_session, monkeypatch):
    deleted_ticket_ids = []

    def fake_delete_ticket_document(client, ticket_id):
        deleted_ticket_ids.append(ticket_id)

    monkeypatch.setattr(
        "app.outbox.processor.delete_ticket_document",
        fake_delete_ticket_document,
    )

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

    service.delete_ticket(ticket_id)

    processor = OutboxProcessor(
        db=db_session,
        search_client=FakeSearchClient(),
    )

    result = processor.process_events(limit=10)

    events = (
        db_session.query(OutboxEvent)
        .order_by(OutboxEvent.id)
        .all()
    )

    assert result.processed == 2
    assert result.failed == 0
    assert deleted_ticket_ids == [ticket_id]
    assert [event.status for event in events] == ["processed", "processed"]


def test_processor_marks_event_failed_when_indexing_fails(db_session, monkeypatch):
    def fake_ticket_to_search_document(ticket):
        return {
            "id": ticket.id,
            "title": ticket.title,
        }

    def fake_index_ticket_document(client, document):
        raise RuntimeError("Elasticsearch is down")

    monkeypatch.setattr(
        "app.outbox.processor.ticket_to_search_document",
        fake_ticket_to_search_document,
    )
    monkeypatch.setattr(
        "app.outbox.processor.index_ticket_document",
        fake_index_ticket_document,
    )

    service = TicketService(db_session)
    service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Cannot login",
            description="Login fails.",
            status="open",
            priority="high",
            category="auth",
            tags=["login"],
        )
    )

    processor = OutboxProcessor(
        db=db_session,
        search_client=FakeSearchClient(),
    )

    result = processor.process_events(limit=10)

    event = db_session.query(OutboxEvent).one()

    assert result.processed == 0
    assert result.failed == 1
    assert event.status == "failed"
    assert event.retry_count == 1
    assert event.last_error == "Elasticsearch is down"
    assert event.processed_at is None


def test_processor_marks_unknown_event_type_failed(db_session):
    repository = OutboxEventRepository(db_session)
    repository.add_event(
        aggregate_type="ticket",
        aggregate_id=123,
        event_type="ticket.archived",
        payload={},
    )
    db_session.commit()

    processor = OutboxProcessor(
        db=db_session,
        search_client=FakeSearchClient(),
    )

    result = processor.process_events(limit=10)

    event = db_session.query(OutboxEvent).one()

    assert result.processed == 0
    assert result.failed == 1
    assert event.status == "failed"
    assert event.retry_count == 1
    assert "Unsupported outbox event type" in event.last_error


def test_processor_retries_failed_event_successfully(db_session, monkeypatch):
    indexed_documents = []

    def fake_ticket_to_search_document(ticket):
        return {
            "id": ticket.id,
            "title": ticket.title,
        }

    def fake_index_ticket_document(client, document):
        indexed_documents.append(document)

    monkeypatch.setattr(
        "app.outbox.processor.ticket_to_search_document",
        fake_ticket_to_search_document,
    )
    monkeypatch.setattr(
        "app.outbox.processor.index_ticket_document",
        fake_index_ticket_document,
    )

    service = TicketService(db_session)
    ticket = service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Retry me",
            description="This ticket should be indexed after retry.",
            status="open",
            priority="high",
            category="auth",
            tags=["retry"],
        )
    )

    event = db_session.query(OutboxEvent).one()

    repository = OutboxEventRepository(db_session)
    repository.mark_failed(event, error=RuntimeError("temporary failure"))
    db_session.commit()

    processor = OutboxProcessor(
        db=db_session,
        search_client=FakeSearchClient(),
    )

    result = processor.process_events(
        limit=10,
        max_retry_count=3,
    )

    db_session.refresh(event)

    assert result.processed == 1
    assert result.failed == 0
    assert indexed_documents == [
        {
            "id": ticket.id,
            "title": "Retry me",
        }
    ]
    assert event.status == "processed"
    assert event.retry_count == 1
    assert event.last_error is None
    assert event.processed_at is not None


def test_processor_does_not_retry_failed_event_after_max_retry_count(
    db_session,
    monkeypatch,
):
    index_calls = []

    def fake_ticket_to_search_document(ticket):
        return {
            "id": ticket.id,
            "title": ticket.title,
        }

    def fake_index_ticket_document(client, document):
        index_calls.append(document)

    monkeypatch.setattr(
        "app.outbox.processor.ticket_to_search_document",
        fake_ticket_to_search_document,
    )
    monkeypatch.setattr(
        "app.outbox.processor.index_ticket_document",
        fake_index_ticket_document,
    )

    service = TicketService(db_session)
    service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Do not retry me",
            description="This event has exhausted retries.",
            status="open",
            priority="high",
            category="auth",
            tags=["retry"],
        )
    )

    event = db_session.query(OutboxEvent).one()

    repository = OutboxEventRepository(db_session)
    repository.mark_failed(event, error=RuntimeError("failure 1"))
    repository.mark_failed(event, error=RuntimeError("failure 2"))
    repository.mark_failed(event, error=RuntimeError("failure 3"))
    db_session.commit()

    processor = OutboxProcessor(
        db=db_session,
        search_client=FakeSearchClient(),
    )

    result = processor.process_events(
        limit=10,
        max_retry_count=3,
    )

    db_session.refresh(event)

    assert result.processed == 0
    assert result.failed == 0
    assert index_calls == []
    assert event.status == "failed"
    assert event.retry_count == 3


def test_processor_recovers_stuck_processing_event(db_session, monkeypatch):
    indexed_documents = []

    def fake_ticket_to_search_document(ticket):
        return {
            "id": ticket.id,
            "title": ticket.title,
        }

    def fake_index_ticket_document(client, document):
        indexed_documents.append(document)

    monkeypatch.setattr(
        "app.outbox.processor.ticket_to_search_document",
        fake_ticket_to_search_document,
    )
    monkeypatch.setattr(
        "app.outbox.processor.index_ticket_document",
        fake_index_ticket_document,
    )

    service = TicketService(db_session)
    ticket = service.create_ticket(
        TicketCreateRequest(
            user_id=1,
            title="Recover me",
            description="This processing event should be recovered.",
            status="open",
            priority="high",
            category="auth",
            tags=["recovery"],
        )
    )

    event = db_session.query(OutboxEvent).one()

    repository = OutboxEventRepository(db_session)
    repository.mark_processing(event)
    db_session.commit()

    event.updated_at = utc_now_naive() - timedelta(seconds=600)
    db_session.commit()

    processor = OutboxProcessor(
        db=db_session,
        search_client=FakeSearchClient(),
    )

    result = processor.process_events(
        limit=10,
        max_retry_count=3,
        processing_timeout_seconds=300,
    )

    db_session.refresh(event)

    assert result.processed == 1
    assert result.failed == 0
    assert indexed_documents == [
        {
            "id": ticket.id,
            "title": "Recover me",
        }
    ]
    assert event.status == "processed"
    assert event.processed_at is not None
    assert event.last_error is None