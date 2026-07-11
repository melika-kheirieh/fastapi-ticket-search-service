from app.schemas.ticket import TicketResponse

USER_HEADERS = {
    "X-User-ID": "7",
}

OTHER_USER_HEADERS = {
    "X-User-ID": "8",
}

ADMIN_HEADERS = {
    "X-User-ID": "1",
    "X-User-Role": "admin",
}


def ticket_response(**overrides) -> TicketResponse:
    data = {
        "id": 1,
        "user_id": 7,
        "title": "Payment failed",
        "description": "Payment was not captured",
        "status": "open",
        "priority": "high",
        "category": "billing",
        "tags": ["payment", "checkout"],
        "created_at": "2026-06-23T10:30:00+00:00",
        "updated_at": "2026-06-23T10:35:00+00:00",
    }
    data.update(overrides)
    return TicketResponse(**data)
