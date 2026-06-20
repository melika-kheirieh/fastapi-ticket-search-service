from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ticket import TicketCreateRequest, TicketResponse
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreateRequest,
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    return service.create_ticket(payload)
