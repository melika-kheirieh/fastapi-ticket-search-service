from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ticket import TicketCreateRequest, TicketResponse, TicketUpdateRequest
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
def create_ticket(
    payload: TicketCreateRequest,
    db: Session = Depends(get_db),
):
    service = TicketService(db)
    return service.create_ticket(payload)


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):  
    if limit > 100:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 100")
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be at least 1")

    service = TicketService(db)
    return service.list_tickets(
        status=status,
        priority=priority,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    service = TicketService(db)
    ticket = service.get_ticket_by_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdateRequest,
    db: Session = Depends(get_db),
):
    service = TicketService(db)
    ticket = service.update_ticket(ticket_id, payload)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    service = TicketService(db)
    deleted = service.delete_ticket(ticket_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Ticket not found")
    