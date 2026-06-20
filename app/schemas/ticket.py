from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    status: TicketStatus = TicketStatus.open
    priority: TicketPriority = TicketPriority.medium
    category: str = Field(..., min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list)


class TicketResponse(BaseModel):
    id: int
    user_id: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
