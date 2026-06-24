import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.ticket import Ticket
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


def test_create_ticket_syncs_created_ticket_to_search(db_session, monkeypatch):
    sync_calls = []
    client = object()

    def fake_create_elasticsearch_client():
        return client

    def fake_index_ticket_document(search_client, document):
        sync_calls.append(
            {
                "client": search_client,
                "document": document,
            }
        )

    monkeypatch.setattr(
        "app.services.ticket_service.create_elasticsearch_client",
        fake_create_elasticsearch_client,
    )
    monkeypatch.setattr(
        "app.services.ticket_service.index_ticket_document",
        fake_index_ticket_document,
    )

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

    assert ticket.id is not None
    assert sync_calls[0]["client"] is client
    assert sync_calls[0]["document"]["id"] == ticket.id
    assert sync_calls[0]["document"]["title"] == "Payment failed"


def test_create_ticket_persists_when_search_sync_fails(db_session, monkeypatch):
    def fake_create_elasticsearch_client():
        raise RuntimeError("Elasticsearch is unavailable")

    monkeypatch.setattr(
        "app.services.ticket_service.create_elasticsearch_client",
        fake_create_elasticsearch_client,
    )

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

    assert persisted_ticket is not None
    assert persisted_ticket.title == "Payment failed"
