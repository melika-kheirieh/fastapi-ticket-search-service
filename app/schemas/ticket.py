from datetime import datetime
from pydantic import BaseModel


class TicketCreateRequest(BaseModel):
    user_id: str
    title: str
    description: str
    status: str
    priority: str
    category: str
    tags: list[str]


class TicketResponse(BaseModel):
    id: int
    user_id: str
    title: str
    description: str
    status: str
    priority: str
    category: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
