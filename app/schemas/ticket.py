from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TicketCreateRequest(BaseModel):
    user_id: int = Field(..., gt=0)  
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    status: str = Field(default="open", max_length=50)
    priority: str = Field(default="medium", max_length=50)
    category: str = Field(..., min_length=1, max_length=100)
    tags: list[str] = Field(default_factory=list)


class TicketResponse(BaseModel):
    id: int
    user_id: int
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


class TicketUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)
    status: str | None = Field(None, max_length=50)
    priority: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None