from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.ticket import Ticket


def ticket_to_search_document(ticket: Ticket) -> dict[str, Any]:
    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "tags": ticket.tags,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }