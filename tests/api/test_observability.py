from fastapi.testclient import TestClient

from app.main import app
from app.search.dependencies import get_elasticsearch_client


class HealthySearchClient:
    def ping(self):
        return True


class UnhealthySearchClient:
    def ping(self):
        return False


class FailingSearchClient:
    def ping(self):
        raise ConnectionError("Elasticsearch is unavailable")


def test_request_id_header_is_added_to_response():
    app.dependency_overrides[get_elasticsearch_client] = lambda: HealthySearchClient()

    client = TestClient(app)

    response = client.get(
        "/health/search",
        headers={"X-Request-ID": "req-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"


def test_search_health_returns_ok_when_elasticsearch_is_available():
    app.dependency_overrides[get_elasticsearch_client] = lambda: HealthySearchClient()

    client = TestClient(app)
    response = client.get("/health/search")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_health_returns_503_when_elasticsearch_ping_returns_false():
    app.dependency_overrides[get_elasticsearch_client] = lambda: UnhealthySearchClient()

    client = TestClient(app)
    response = client.get("/health/search")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "reason": "elasticsearch_ping_returned_false",
    }


def test_search_health_returns_503_when_elasticsearch_ping_raises_error():
    app.dependency_overrides[get_elasticsearch_client] = lambda: FailingSearchClient()

    client = TestClient(app)
    response = client.get("/health/search")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "reason": "elasticsearch_ping_failed",
        "error": "ConnectionError",
    }