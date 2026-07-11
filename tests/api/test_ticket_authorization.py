from app.main import app
from app.search.dependencies import get_elasticsearch_client

from tests.api.support import (
    ADMIN_HEADERS,
    USER_HEADERS,
    ticket_response,
)


def test_create_ticket_rejects_regular_user_creating_for_another_user(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def create_ticket(self, payload):
            raise AssertionError("TicketService should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

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


def test_create_ticket_allows_admin_to_create_for_another_user(client, monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def create_ticket(self, payload):
            calls["payload"] = payload
            return ticket_response(user_id=payload.user_id)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

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


def test_list_tickets_for_regular_user_forces_current_user_filter(client, monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            calls["db"] = db

        def list_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return [ticket_response(user_id=7)]

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

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


def test_list_tickets_allows_regular_user_to_request_own_user_id(client, monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            pass

        def list_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return [ticket_response(user_id=7)]

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.get(
        "/tickets",
        headers=USER_HEADERS,
        params={
            "user_id": 7,
        },
    )

    assert response.status_code == 200
    assert calls["kwargs"]["user_id"] == 7


def test_list_tickets_rejects_regular_user_requesting_another_user_id(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def list_tickets(self, **kwargs):
            raise AssertionError("TicketService should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

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


def test_list_tickets_allows_admin_to_forward_filters_and_pagination(client, monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            calls["db"] = db

        def list_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return [ticket_response(user_id=8)]

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

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


def test_get_ticket_returns_not_found_for_ticket_owned_by_another_user(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.get(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_get_ticket_allows_admin_to_read_ticket_owned_by_another_user(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.get(
        "/tickets/1",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["user_id"] == 8


def test_update_ticket_returns_not_found_for_ticket_owned_by_another_user(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

        def update_ticket(self, ticket_id, payload):
            raise AssertionError("update_ticket should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.patch(
        "/tickets/1",
        headers=USER_HEADERS,
        json={"status": "closed"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_update_ticket_allows_admin_to_update_ticket_owned_by_another_user(client, monkeypatch):
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

    response = client.patch(
        "/tickets/1",
        headers=ADMIN_HEADERS,
        json={"status": "closed"},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == 8
    assert response.json()["status"] == "closed"
    assert calls["ticket_id"] == 1


def test_delete_ticket_returns_not_found_for_ticket_owned_by_another_user(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=8)

        def delete_ticket(self, ticket_id):
            raise AssertionError("delete_ticket should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.delete(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_delete_ticket_allows_admin_to_delete_ticket_owned_by_another_user(client, monkeypatch):
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

    response = client.delete(
        "/tickets/1",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 204
    assert response.content == b""
    assert calls["ticket_id"] == 1


def test_search_tickets_allows_regular_user_to_request_own_user_id(client, monkeypatch):
    calls = {}

    def fake_search_ticket_documents(client, **kwargs):
        calls["kwargs"] = kwargs
        return [ticket_response(user_id=7)]

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

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


def test_search_tickets_rejects_regular_user_requesting_another_user_id(client, monkeypatch):
    def fake_search_ticket_documents(client, **kwargs):
        raise AssertionError("search_ticket_documents should not be called")

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

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


def test_search_tickets_allows_admin_to_forward_requested_user_id(client, monkeypatch):
    calls = {}

    def fake_search_ticket_documents(client, **kwargs):
        calls["kwargs"] = kwargs
        return [ticket_response(user_id=8)]

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

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
