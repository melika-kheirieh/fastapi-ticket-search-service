import pytest
from fastapi.testclient import TestClient

from app.api.tickets import get_db
from app.main import app
from app.schemas.ticket import TicketResponse
from app.search.dependencies import get_elasticsearch_client
from app.search.exceptions import SearchUnavailableError


USER_HEADERS = {
    "X-User-ID": "7",
}

OTHER_USER_HEADERS = {
    "X-User-ID": "8",
}

ADMIN_HEADERS = {
    "X-User-ID": "1",
    "X-User-Role": "admin",
}


@pytest.fixture(autouse=True)
def override_db_dependency():
    app.dependency_overrides[get_db] = lambda: object()
    yield
    app.dependency_overrides.clear()


def ticket_response(**overrides):
    data = {
        "id": 1,
        "user_id": 7,
        "title": "Payment failed",
        "description": "Payment was not captured",
        "status": "open",
        "priority": "high",
        "category": "billing",
        "tags": ["payment", "checkout"],
        "created_at": "2026-06-23T10:30:00+00:00",
        "updated_at": "2026-06-23T10:35:00+00:00",
    }
    data.update(overrides)
    return TicketResponse(**data)


def test_create_ticket_returns_created_ticket(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            calls["db"] = db

        def create_ticket(self, payload):
            calls["payload"] = payload
            return ticket_response(
                user_id=payload.user_id,
                title=payload.title,
                description=payload.description,
                status=payload.status,
                priority=payload.priority,
                category=payload.category,
                tags=payload.tags,
            )

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.post(
        "/tickets",
        headers=USER_HEADERS,
        json={
            "user_id": 7,
            "title": "Payment failed",
            "description": "Payment was not captured",
            "status": "open",
            "priority": "high",
            "category": "billing",
            "tags": ["payment", "checkout"],
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Payment failed"
    assert calls["payload"].user_id == 7
    assert calls["payload"].tags == ["payment", "checkout"]


def test_create_ticket_rejects_regular_user_creating_for_another_user(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def create_ticket(self, payload):
            raise AssertionError("TicketService should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.post(
        "/tickets",
        headers=USER_HEADERS,
        json={
            "user_id": 8,
            "title": "Payment failed",
            "description": "Payment was not captured",
            "status": "open",
            "priority": "high",
            "category": "billing",
            "tags": ["payment", "checkout"],
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Not allowed to create ticket for another user",
    }


def test_create_ticket_allows_admin_to_create_for_another_user(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def create_ticket(self, payload):
            calls["payload"] = payload
            return ticket_response(user_id=payload.user_id)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.post(
        "/tickets",
        headers=ADMIN_HEADERS,
        json={
            "user_id": 8,
            "title": "Payment failed",
            "description": "Payment was not captured",
            "status": "open",
            "priority": "high",
            "category": "billing",
            "tags": ["payment", "checkout"],
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == 8
    assert calls["payload"].user_id == 8


def test_list_tickets_for_regular_user_forces_current_user_filter(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            calls["db"] = db

        def list_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return [ticket_response(user_id=7)]

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets",
        headers=USER_HEADERS,
        params={
            "status": "open",
            "priority": "high",
            "category": "billing",
            "limit": 10,
            "offset": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 1
    assert calls["kwargs"] == {
        "status": "open",
        "priority": "high",
        "category": "billing",
        "user_id": 7,
        "limit": 10,
        "offset": 20,
    }


def test_list_tickets_allows_regular_user_to_request_own_user_id(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def list_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return [ticket_response(user_id=7)]

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets",
        headers=USER_HEADERS,
        params={
            "user_id": 7,
        },
    )

    assert response.status_code == 200
    assert calls["kwargs"]["user_id"] == 7


def test_list_tickets_rejects_regular_user_requesting_another_user_id(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def list_tickets(self, **kwargs):
            raise AssertionError("TicketService should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets",
        headers=USER_HEADERS,
        params={
            "user_id": 8,
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Not allowed to access tickets for another user",
    }


def test_list_tickets_allows_admin_to_forward_filters_and_pagination(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            calls["db"] = db

        def list_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return [ticket_response(user_id=8)]

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets",
        headers=ADMIN_HEADERS,
        params={
            "status": "open",
            "priority": "high",
            "category": "billing",
            "user_id": 8,
            "limit": 10,
            "offset": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 1
    assert calls["kwargs"] == {
        "status": "open",
        "priority": "high",
        "category": "billing",
        "user_id": 8,
        "limit": 10,
        "offset": 20,
    }


def test_get_ticket_returns_ticket_for_owner(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=7)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["user_id"] == 7


def test_get_ticket_returns_not_found_when_service_returns_none(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return None

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets/999",
        headers=USER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_get_ticket_returns_not_found_for_ticket_owned_by_another_user(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_get_ticket_allows_admin_to_read_ticket_owned_by_another_user(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.get(
        "/tickets/1",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["user_id"] == 8


def test_update_ticket_updates_ticket_for_owner(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=7)

        def update_ticket(self, ticket_id, payload):
            calls["ticket_id"] = ticket_id
            calls["payload"] = payload
            return ticket_response(id=ticket_id, user_id=7, status=payload.status)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.patch(
        "/tickets/1",
        headers=USER_HEADERS,
        json={"status": "closed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    assert calls["ticket_id"] == 1
    assert calls["payload"].status == "closed"


def test_update_ticket_returns_not_found_for_ticket_owned_by_another_user(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

        def update_ticket(self, ticket_id, payload):
            raise AssertionError("update_ticket should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.patch(
        "/tickets/1",
        headers=USER_HEADERS,
        json={"status": "closed"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_update_ticket_allows_admin_to_update_ticket_owned_by_another_user(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

        def update_ticket(self, ticket_id, payload):
            calls["ticket_id"] = ticket_id
            return ticket_response(id=ticket_id, user_id=8, status=payload.status)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.patch(
        "/tickets/1",
        headers=ADMIN_HEADERS,
        json={"status": "closed"},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == 8
    assert response.json()["status"] == "closed"
    assert calls["ticket_id"] == 1


def test_delete_ticket_returns_no_content(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=7)

        def delete_ticket(self, ticket_id):
            calls["ticket_id"] = ticket_id
            return True

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.delete(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 204
    assert response.content == b""
    assert calls["ticket_id"] == 1


def test_delete_ticket_returns_not_found_for_ticket_owned_by_another_user(monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

        def delete_ticket(self, ticket_id):
            raise AssertionError("delete_ticket should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.delete(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_delete_ticket_allows_admin_to_delete_ticket_owned_by_another_user(monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

        def delete_ticket(self, ticket_id):
            calls["ticket_id"] = ticket_id
            return True

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    client = TestClient(app)
    response = client.delete(
        "/tickets/1",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 204
    assert response.content == b""
    assert calls["ticket_id"] == 1


def test_search_tickets_for_regular_user_forces_current_user_filter(monkeypatch):
    calls = {}

    def fake_search_ticket_documents(client, **kwargs):
        calls["client"] = client
        calls["kwargs"] = kwargs
        return [ticket_response(user_id=7)]

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

    client = TestClient(app)
    response = client.get(
        "/tickets/search",
        headers=USER_HEADERS,
        params={
            "q": "payment",
            "tag": "payment",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["user_id"] == 7
    assert calls["kwargs"]["query"] == "payment"
    assert calls["kwargs"]["tag"] == "payment"
    assert calls["kwargs"]["user_id"] == 7
    assert calls["kwargs"]["limit"] == 5


def test_search_tickets_allows_regular_user_to_request_own_user_id(monkeypatch):
    calls = {}

    def fake_search_ticket_documents(client, **kwargs):
        calls["kwargs"] = kwargs
        return [ticket_response(user_id=7)]

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

    client = TestClient(app)
    response = client.get(
        "/tickets/search",
        headers=USER_HEADERS,
        params={
            "q": "payment",
            "user_id": 7,
        },
    )

    assert response.status_code == 200
    assert calls["kwargs"]["user_id"] == 7


def test_search_tickets_rejects_regular_user_requesting_another_user_id(monkeypatch):
    def fake_search_ticket_documents(client, **kwargs):
        raise AssertionError("search_ticket_documents should not be called")

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

    client = TestClient(app)
    response = client.get(
        "/tickets/search",
        headers=USER_HEADERS,
        params={
            "q": "payment",
            "user_id": 8,
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Not allowed to access tickets for another user",
    }


def test_search_tickets_allows_admin_to_forward_requested_user_id(monkeypatch):
    calls = {}

    def fake_search_ticket_documents(client, **kwargs):
        calls["kwargs"] = kwargs
        return [ticket_response(user_id=8)]

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

    client = TestClient(app)
    response = client.get(
        "/tickets/search",
        headers=ADMIN_HEADERS,
        params={
            "q": "payment",
            "user_id": 8,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["user_id"] == 8
    assert calls["kwargs"]["user_id"] == 8


def test_search_tickets_returns_503_when_search_backend_is_unavailable(monkeypatch):
    def fake_search_ticket_documents(client, **kwargs):
        raise SearchUnavailableError("Search backend is unavailable")

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

    client = TestClient(app)
    response = client.get(
        "/tickets/search",
        headers=USER_HEADERS,
        params={"q": "payment"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Search is temporarily unavailable"}