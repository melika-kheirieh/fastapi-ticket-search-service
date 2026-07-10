from fastapi.testclient import TestClient

from app.main import app


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

    client.get("/health")
    client.get("/metrics")

    response = client.get("/metrics")

    assert 'route="/health"' in response.text