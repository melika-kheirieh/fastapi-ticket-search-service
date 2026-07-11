from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser


test_app = FastAPI()


@test_app.get("/me")
def read_current_user(
    current_user: CurrentUser = Depends(get_current_user),
):
    return {
        "user_id": current_user.user_id,
        "role": current_user.role,
        "is_admin": current_user.is_admin,
    }


def test_current_user_defaults_to_user_role():
    client = TestClient(test_app)

    response = client.get(
        "/me",
        headers={
            "X-User-ID": "123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 123,
        "role": "user",
        "is_admin": False,
    }


def test_current_user_accepts_admin_role():
    client = TestClient(test_app)

    response = client.get(
        "/me",
        headers={
            "X-User-ID": "123",
            "X-User-Role": "admin",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 123,
        "role": "admin",
        "is_admin": True,
    }


def test_current_user_requires_user_id_header():
    client = TestClient(test_app)

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Missing authentication context",
    }


def test_current_user_rejects_invalid_user_id():
    client = TestClient(test_app)

    response = client.get(
        "/me",
        headers={
            "X-User-ID": "not-a-number",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid user id",
    }


def test_current_user_rejects_non_positive_user_id():
    client = TestClient(test_app)

    response = client.get(
        "/me",
        headers={
            "X-User-ID": "0",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid user id",
    }


def test_current_user_rejects_invalid_role():
    client = TestClient(test_app)

    response = client.get(
        "/me",
        headers={
            "X-User-ID": "123",
            "X-User-Role": "superuser",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid user role",
    }