import pytest
from fastapi.testclient import TestClient

from app.api.tickets import get_db
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def override_db_dependency():
    app.dependency_overrides[get_db] = lambda: object()

    try:
        yield
    finally:
        app.dependency_overrides.clear()
