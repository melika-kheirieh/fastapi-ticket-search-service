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
        query: str,
        status: str | None,
        priority: str | None,
        category: str | None,
        tag: str | None,
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
            "limit": 5,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 3
    assert response.json()[0]["title"] == "Payment failed"

    assert calls == [
        {
            "client": fake_client,
            "query": "payment",
            "status": "open",
            "priority": "high",
            "category": "payment",
            "tag": "checkout",
            "limit": 5,
            "offset": 0,
        }
    ]
