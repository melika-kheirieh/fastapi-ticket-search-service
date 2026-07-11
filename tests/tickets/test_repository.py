from datetime import datetime, timezone

from app.models.ticket import Ticket
from app.repositories.ticket_repository import TicketRepository


def add_ticket(
    db_session,
    *,
    user_id: int,
    title: str,
    status: str,
    priority: str,
    category: str,
    created_at: datetime,
) -> Ticket:
    ticket = Ticket(
        user_id=user_id,
        title=title,
        description=f"{title} description",
        status=status,
        priority=priority,
        category=category,
        tags=[category],
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


def test_get_all_filters_by_ticket_fields(db_session):
    add_ticket(
        db_session,
        user_id=7,
        title="Payment failed",
        status="open",
        priority="high",
        category="billing",
        created_at=datetime(2026, 6, 23, 10, 0, tzinfo=timezone.utc),
    )
    add_ticket(
        db_session,
        user_id=8,
        title="Login issue",
        status="open",
        priority="high",
        category="auth",
        created_at=datetime(2026, 6, 23, 11, 0, tzinfo=timezone.utc),
    )

    repository = TicketRepository(db_session)

    tickets = repository.get_all(
        status="open",
        priority="high",
        category="billing",
        user_id=7,
    )

    assert len(tickets) == 1
    assert tickets[0].title == "Payment failed"


def test_get_all_orders_by_newest_ticket_and_applies_pagination(db_session):
    add_ticket(
        db_session,
        user_id=7,
        title="Old ticket",
        status="open",
        priority="low",
        category="support",
        created_at=datetime(2026, 6, 21, 10, 0, tzinfo=timezone.utc),
    )
    add_ticket(
        db_session,
        user_id=7,
        title="Middle ticket",
        status="open",
        priority="medium",
        category="support",
        created_at=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
    )
    add_ticket(
        db_session,
        user_id=7,
        title="Newest ticket",
        status="open",
        priority="high",
        category="support",
        created_at=datetime(2026, 6, 23, 10, 0, tzinfo=timezone.utc),
    )

    repository = TicketRepository(db_session)

    tickets = repository.get_all(limit=1, offset=1)

    assert [ticket.title for ticket in tickets] == ["Middle ticket"]
