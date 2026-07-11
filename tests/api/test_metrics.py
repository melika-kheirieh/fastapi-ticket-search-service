import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.search.dependencies import get_elasticsearch_client
from app.search.exceptions import SearchUnavailableError


USER_HEADERS = {
    "X-User-ID": "1",
}


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


class FakeOutboxCountResult:
    def all(self):
        return [
            ("pending", 2),
            ("processing", 1),
            ("processed", 5),
            ("failed", 0),
        ]


class FakeOutboxDbSession:
    def execute(self, stmt):
        return FakeOutboxCountResult()


@pytest.fixture
def metrics_db_override():
    app.dependency_overrides[get_db] = lambda: FakeOutboxDbSession()


def test_metrics_endpoint_returns_prometheus_output(metrics_db_override):
    client = TestClient(app)

    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


def test_http_metrics_use_route_template_not_raw_path(metrics_db_override):
    client = TestClient(app)

    client.get("/metrics")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'route="/metrics"' in response.text


def test_search_success_metrics_are_recorded(metrics_db_override):
    app.dependency_overrides[get_elasticsearch_client] = lambda: FakeSearchClient()

    client = TestClient(app)

    search_response = client.get("/tickets/search?q=payment", headers=USER_HEADERS)
    assert search_response.status_code == 200

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert "search_requests_total" in metrics_response.text
    assert 'search_requests_total{status="success"}' in metrics_response.text
    assert "search_request_duration_seconds" in metrics_response.text
    assert 'search_request_duration_seconds_count{status="success"}' in metrics_response.text


def test_search_unavailable_metrics_are_recorded(metrics_db_override, monkeypatch):
    def fake_search_ticket_documents(**kwargs):
        raise SearchUnavailableError("Search backend is unavailable")

    monkeypatch.setattr(
        "app.api.tickets.search_ticket_documents",
        fake_search_ticket_documents,
    )

    client = TestClient(app)

    search_response = client.get("/tickets/search?q=payment", headers=USER_HEADERS)
    assert search_response.status_code == 503

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert "search_unavailable_total" in metrics_response.text
    assert 'search_requests_total{status="unavailable"}' in metrics_response.text
    assert 'search_request_duration_seconds_count{status="unavailable"}' in metrics_response.text


def test_metrics_endpoint_exposes_outbox_status_gauge(metrics_db_override):
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "outbox_events_by_status" in response.text
    assert 'outbox_events_by_status{status="pending"} 2.0' in response.text
    assert 'outbox_events_by_status{status="processing"} 1.0' in response.text
    assert 'outbox_events_by_status{status="processed"} 5.0' in response.text
    assert 'outbox_events_by_status{status="failed"} 0.0' in response.text