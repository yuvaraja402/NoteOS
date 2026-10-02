from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Color = Literal["sea", "sky", "coral", "citrus"]


class NoteBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(default="", max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    color: Color = "sea"
    is_pinned: bool = False

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags):
        if any(not tag.strip() or len(tag) > 32 for tag in tags):
            raise ValueError("Tags must contain 1 to 32 characters.")
        return tags


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, max_length=20000)
    tags: list[str] | None = Field(default=None, max_length=10)
    color: Color | None = None
    is_pinned: bool | None = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags):
        return NoteBase.validate_tags(tags) if tags is not None else tags


class NoteRead(NoteBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
