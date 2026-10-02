from datetime import datetime

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    color: str = "sea"
    is_pinned: bool = False


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = None
    tags: list[str] | None = None
    color: str | None = None
    is_pinned: bool | None = None


class NoteRead(NoteBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
