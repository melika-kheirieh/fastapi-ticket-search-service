from fastapi.testclient import TestClient

from app.main import app
from app.search.dependencies import get_elasticsearch_client
from app.search.exceptions import SearchUnavailableError


class FakeSearchClient:
    def search(self, index: str, body: dict) -> dict:
        return {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": 1,
                            "user_id": 1,
                            "title": "Payment failed",
                            "description": "Customer payment failed during checkout.",
                            "status": "open",
                            "priority": "high",
                            "category": "billing",
                            "tags": ["payment", "checkout"],
                            "created_at": "2026-07-10T07:00:00+00:00",
                            "updated_at": "2026-07-10T07:00:00+00:00",
                        }
                    }
                ]
            }
        }


def test_metrics_endpoint_returns_prometheus_output():
    client = TestClient(app)

    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


def test_http_metrics_use_route_template_not_raw_path():
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'route="/metrics"' in response.text


def test_search_success_metrics_are_recorded():
    app.dependency_overrides[get_elasticsearch_client] = lambda: FakeSearchClient()

    try:
        client = TestClient(app)

        search_response = client.get("/tickets/search?q=payment")
        assert search_response.status_code == 200

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "search_requests_total" in metrics_response.text
        assert 'search_requests_total{status="success"}' in metrics_response.text
        assert "search_request_duration_seconds" in metrics_response.text
        assert 'search_request_duration_seconds_count{status="success"}' in metrics_response.text
    finally:
        app.dependency_overrides.clear()


def test_search_unavailable_metrics_are_recorded(monkeypatch):
    def fake_search_ticket_documents(**kwargs):
        raise SearchUnavailableError("Search backend is unavailable")

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )

    client = TestClient(app)

    search_response = client.get("/tickets/search?q=payment")
    assert search_response.status_code == 503

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert "search_unavailable_total" in metrics_response.text
    assert 'search_requests_total{status="unavailable"}' in metrics_response.text
    assert 'search_request_duration_seconds_count{status="unavailable"}' in metrics_response.text