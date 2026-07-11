from app.main import app
from app.search.dependencies import get_elasticsearch_client
from app.search.exceptions import SearchUnavailableError

from tests.api.support import USER_HEADERS, ticket_response


def test_search_tickets_for_regular_user_forces_current_user_filter(client, monkeypatch):
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


def test_search_tickets_returns_503_when_search_backend_is_unavailable(client, monkeypatch):
    def fake_search_ticket_documents(client, **kwargs):
        raise SearchUnavailableError("Search backend is unavailable")

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )
    app.dependency_overrides[get_elasticsearch_client] = lambda: object()

    response = client.get(
        "/tickets/search",
        headers=USER_HEADERS,
        params={"q": "payment"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Search is temporarily unavailable"}
