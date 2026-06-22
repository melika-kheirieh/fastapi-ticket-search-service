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

from app.db.session import get_db
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketResponse,
    TicketUpdateRequest,
)
from app.services.ticket_service import TicketService


router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post(
    "",
    response_model=TicketResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_ticket(
    payload: TicketCreateRequest,
    db: Session = Depends(get_db),
):
    service = TicketService(db)
    return service.create_ticket(payload)


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    status: str | None = Query(
        default=None,
        min_length=1,
        max_length=32,
    ),
    priority: str | None = Query(
        default=None,
        min_length=1,
        max_length=32,
    ),
    category: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    service = TicketService(db)

    return service.list_tickets(
        status=status,
        priority=priority,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    service = TicketService(db)
    ticket = service.get_ticket_by_id(ticket_id)

    if not ticket:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    payload: TicketUpdateRequest,
    ticket_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    service = TicketService(db)
    ticket = service.update_ticket(ticket_id, payload)

    if not ticket:
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
) -> Response:
    service = TicketService(db)
    deleted = service.delete_ticket(ticket_id)

    if not deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)