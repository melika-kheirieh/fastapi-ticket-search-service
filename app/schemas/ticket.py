from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TicketCreateRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    status: str = Field(default="open", min_length=1, max_length=32)
    priority: str = Field(default="medium", min_length=1, max_length=32)
    category: str = Field(..., min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list)


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class TicketUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)
    status: str | None = Field(None, min_length=1, max_length=32)
    priority: str | None = Field(None, min_length=1, max_length=32)
    category: str | None = Field(None, min_length=1, max_length=64)
    tags: list[str] | None = None

    @model_validator(mode="after")
    def require_at_least_one_value(self) -> "TicketUpdateRequest":
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("At least one field must be provided")
        return self