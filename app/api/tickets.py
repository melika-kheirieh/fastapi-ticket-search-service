import logging
import time
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status as http_status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.db.session import get_db
from app.observability.metrics import record_search_request, record_search_unavailable
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketResponse,
    TicketUpdateRequest,
)
from app.search.dependencies import get_elasticsearch_client
from app.search.exceptions import SearchUnavailableError
from app.search.queries import search_tickets as search_ticket_documents
from app.services.ticket_service import TicketService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def _resolve_visible_user_id(
    *,
    current_user: CurrentUser,
    requested_user_id: int | None,
) -> int | None:
    if current_user.is_admin:
        return requested_user_id

    if requested_user_id is not None and requested_user_id != current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access tickets for another user",
        )

    return current_user.user_id


def _ensure_create_user_id_is_allowed(
    *,
    current_user: CurrentUser,
    requested_user_id: int,
) -> None:
    if current_user.is_admin:
        return

    if requested_user_id != current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Not allowed to create ticket for another user",
        )


def _get_ticket_user_id(ticket) -> int:
    if isinstance(ticket, dict):
        return ticket["user_id"]

    return ticket.user_id


def _ensure_ticket_is_visible(
    *,
    ticket,
    current_user: CurrentUser,
) -> None:
    if current_user.is_admin:
        return

    if _get_ticket_user_id(ticket) != current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )


@router.post(
    "",
    response_model=TicketResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_ticket(
    payload: TicketCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _ensure_create_user_id_is_allowed(
        current_user=current_user,
        requested_user_id=payload.user_id,
    )

    service = TicketService(db)
    return service.create_ticket(payload)


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    status: str | None = Query(default=None, min_length=1, max_length=32),
    priority: str | None = Query(default=None, min_length=1, max_length=32),
    category: str | None = Query(default=None, min_length=1, max_length=64),
    user_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    visible_user_id = _resolve_visible_user_id(
        current_user=current_user,
        requested_user_id=user_id,
    )

    service = TicketService(db)

    return service.list_tickets(
        status=status,
        priority=priority,
        category=category,
        user_id=visible_user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=list[TicketResponse])
def search_tickets(
    q: str | None = Query(default=None, min_length=1, max_length=200),
    status: str | None = Query(default=None, min_length=1, max_length=32),
    priority: str | None = Query(default=None, min_length=1, max_length=32),
    category: str | None = Query(default=None, min_length=1, max_length=64),
    tag: str | None = Query(default=None, min_length=1, max_length=64),
    user_id: int | None = Query(default=None, gt=0),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search_client=Depends(get_elasticsearch_client),
    current_user: CurrentUser = Depends(get_current_user),
):
    visible_user_id = _resolve_visible_user_id(
        current_user=current_user,
        requested_user_id=user_id,
    )

    started_at = time.perf_counter()

    try:
        results = search_ticket_documents(
            client=search_client,
            query=q,
            status=status,
            priority=priority,
            category=category,
            tag=tag,
            user_id=visible_user_id,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            offset=offset,
        )
    except SearchUnavailableError as exc:
        duration_seconds = time.perf_counter() - started_at

        record_search_request(
            status="unavailable",
            duration_seconds=duration_seconds,
        )
        record_search_unavailable()

        logger.exception(
            "Ticket search unavailable",
            extra={
                "event": "ticket_search_unavailable",
                "query_length": len(q) if q else 0,
                "status": status,
                "priority": priority,
                "category": category,
                "tag": tag,
                "requested_user_id": user_id,
                "visible_user_id": visible_user_id,
                "limit": limit,
                "offset": offset,
            },
        )
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search is temporarily unavailable",
        ) from exc

    duration_seconds = time.perf_counter() - started_at

    record_search_request(
        status="success",
        duration_seconds=duration_seconds,
    )

    return results


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = TicketService(db)
    ticket = service.get_ticket_by_id(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    _ensure_ticket_is_visible(
        ticket=ticket,
        current_user=current_user,
    )

    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    payload: TicketUpdateRequest,
    ticket_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = TicketService(db)
    existing_ticket = service.get_ticket_by_id(ticket_id)

    if existing_ticket is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    _ensure_ticket_is_visible(
        ticket=existing_ticket,
        current_user=current_user,
    )

    ticket = service.update_ticket(ticket_id, payload)

    if ticket is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket


@router.delete(
    "/{ticket_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_ticket(
    ticket_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    service = TicketService(db)
    existing_ticket = service.get_ticket_by_id(ticket_id)

    if existing_ticket is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    _ensure_ticket_is_visible(
        ticket=existing_ticket,
        current_user=current_user,
    )

    deleted = service.delete_ticket(ticket_id)

    if not deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)