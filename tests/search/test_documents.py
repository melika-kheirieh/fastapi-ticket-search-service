from datetime import datetime, timezone
from types import SimpleNamespace

from app.search.documents import ticket_to_search_document


def test_ticket_to_search_document_returns_json_ready_dict():
    created_at = datetime(2026, 6, 23, 10, 30, tzinfo=timezone.utc)
    updated_at = datetime(2026, 6, 23, 11, 45, tzinfo=timezone.utc)

    ticket = SimpleNamespace(
        id=12,
        user_id=7,
        title="Login issue",
        description="User cannot login with valid credentials",
        status="open",
        priority="high",
        category="auth",
        tags=["login", "auth"],
        created_at=created_at,
        updated_at=updated_at,
    )

    document = ticket_to_search_document(ticket)

    assert document == {
        "id": 12,
        "user_id": 7,
        "title": "Login issue",
        "description": "User cannot login with valid credentials",
        "status": "open",
        "priority": "high",
        "category": "auth",
        "tags": ["login", "auth"],
        "created_at": "2026-06-23T10:30:00+00:00",
        "updated_at": "2026-06-23T11:45:00+00:00",
    }