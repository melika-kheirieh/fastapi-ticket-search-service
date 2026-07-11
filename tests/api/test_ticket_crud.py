from tests.api.support import USER_HEADERS, ticket_response


def test_create_ticket_returns_created_ticket(client, monkeypatch):
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


def test_create_ticket_validates_required_fields(client):
    response = client.post(
        "/tickets",
        headers=USER_HEADERS,
        json={
            "user_id": 7,
            "description": "Payment was not captured",
            "category": "billing",
        },
    )

    assert response.status_code == 422


def test_list_tickets_forwards_filters_and_pagination(client, monkeypatch):
    calls = {}

    class FakeTicketService:
        def __init__(self, db):
            calls["db"] = db

        def list_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return [ticket_response()]

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.get(
        "/tickets",
        headers=USER_HEADERS,
        params={
            "status": "open",
            "priority": "high",
            "category": "billing",
            "user_id": 7,
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


def test_list_tickets_validates_pagination(client):
    response = client.get(
        "/tickets",
        headers=USER_HEADERS,
        params={"limit": 0},
    )

    assert response.status_code == 422


def test_get_ticket_returns_ticket_for_owner(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return ticket_response(id=ticket_id, user_id=7)

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.get(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["user_id"] == 7


def test_get_ticket_returns_not_found_when_service_returns_none(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return None

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.get(
        "/tickets/999",
        headers=USER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_update_ticket_updates_ticket_for_owner(client, monkeypatch):
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

    response = client.patch(
        "/tickets/1",
        headers=USER_HEADERS,
        json={"status": "closed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    assert calls["ticket_id"] == 1
    assert calls["payload"].status == "closed"


def test_update_ticket_validates_non_empty_payload(client):
    response = client.patch(
        "/tickets/1",
        headers=USER_HEADERS,
        json={},
    )

    assert response.status_code == 422


def test_update_ticket_returns_not_found_when_service_returns_none(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return None

        def update_ticket(self, ticket_id, payload):
            raise AssertionError("update_ticket should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.patch(
        "/tickets/999",
        headers=USER_HEADERS,
        json={"status": "closed"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


def test_delete_ticket_returns_no_content(client, monkeypatch):
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

    response = client.delete(
        "/tickets/1",
        headers=USER_HEADERS,
    )

    assert response.status_code == 204
    assert response.content == b""
    assert calls["ticket_id"] == 1


def test_delete_ticket_returns_not_found_when_service_returns_false(client, monkeypatch):
    class FakeTicketService:
        def __init__(self, db):
            pass

        def get_ticket_by_id(self, ticket_id):
            return None

        def delete_ticket(self, ticket_id):
            raise AssertionError("delete_ticket should not be called")

    monkeypatch.setattr("app.api.tickets.TicketService", FakeTicketService)

    response = client.delete(
        "/tickets/999",
        headers=USER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}
