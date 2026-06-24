from fastapi.testclient import TestClient

import app.api.tickets as tickets_api
from app.main import app


def test_search_tickets_route_returns_search_results(monkeypatch):
    fake_client = object()
    calls = []

    def fake_create_elasticsearch_client():
        return fake_client

    def fake_search_ticket_documents(
        client,
        query: str | None,
        status: str | None,
        priority: str | None,
        category: str | None,
        tag: str | None,
        user_id: int | None,
        created_from,
        created_to,
        limit: int,
        offset: int,
    ):
        calls.append(
            {
                "client": client,
                "query": query,
                "status": status,
                "priority": priority,
                "category": category,
                "tag": tag,
                "user_id": user_id,
                "created_from": created_from,
                "created_to": created_to,
                "limit": limit,
                "offset": offset,
            }
        )

        return [
            {
                "id": 3,
                "user_id": 21,
                "title": "Payment failed",
                "description": "User payment failed during checkout",
                "status": "open",
                "priority": "high",
                "category": "payment",
                "tags": ["payment", "checkout"],
                "created_at": "2026-06-23T09:11:01.772070Z",
                "updated_at": "2026-06-23T09:11:01.772070Z",
            }
        ]

    monkeypatch.setattr(
        tickets_api,
        "create_elasticsearch_client",
        fake_create_elasticsearch_client,
    )
    monkeypatch.setattr(
        tickets_api,
        "search_ticket_documents",
        fake_search_ticket_documents,
    )

    client = TestClient(app)

    response = client.get(
        "/tickets/search",
        params={
            "q": "payment",
            "status": "open",
            "priority": "high",
            "category": "payment",
            "tag": "checkout",
            "user_id": 21,
            "created_from": "2026-06-01T00:00:00Z",
            "created_to": "2026-06-24T00:00:00Z",
            "limit": 5,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 3
    assert response.json()[0]["title"] == "Payment failed"

    assert calls[0]["client"] is fake_client
    assert calls[0]["query"] == "payment"
    assert calls[0]["status"] == "open"
    assert calls[0]["priority"] == "high"
    assert calls[0]["category"] == "payment"
    assert calls[0]["tag"] == "checkout"
    assert calls[0]["user_id"] == 21
    assert calls[0]["created_from"].isoformat() == "2026-06-01T00:00:00+00:00"
    assert calls[0]["created_to"].isoformat() == "2026-06-24T00:00:00+00:00"
    assert calls[0]["limit"] == 5
    assert calls[0]["offset"] == 0


def test_search_tickets_allows_filter_without_text_query(monkeypatch):
    captured = {}

    def fake_create_elasticsearch_client():
        return object()

    def fake_search_ticket_documents(client, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        "app.api.tickets.create_elasticsearch_client",
        fake_create_elasticsearch_client,
    )
    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )

    client = TestClient(app)

    response = client.get("/tickets/search", params={"status": "open"})

    assert response.status_code == 200
    assert captured["query"] is None
    assert captured["status"] == "open"
    assert captured["user_id"] is None
    assert captured["created_from"] is None
    assert captured["created_to"] is None