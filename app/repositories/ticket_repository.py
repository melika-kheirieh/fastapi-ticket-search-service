from sqlalchemy.orm import Session
from sqlalchemy import select 
from app.models.ticket import Ticket


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def get_all(self, status=None, priority=None, category=None, user_id=None, limit=20, offset=0):
        stmt = select(Ticket) 
        
        if status:
            stmt = stmt.where(Ticket.status == status)
        if priority:
            stmt = stmt.where(Ticket.priority == priority)
        if category:
            stmt = stmt.where(Ticket.category == category)
        if user_id:
            stmt = stmt.where(Ticket.user_id == user_id)  
        
        stmt = stmt.limit(limit).offset(offset).order_by(Ticket.created_at.desc()) 
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_by_id(self, ticket_id: int):
        return self.db.get(Ticket, ticket_id) 

    def update(self, ticket: Ticket) -> Ticket:
        self.db.flush()
        return ticket

    def delete(self, ticket: Ticket) -> None:
        self.db.delete(ticket)
        self.db.flush()
