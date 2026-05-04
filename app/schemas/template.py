"""Pydantic schemas for Template System (v1.1)."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import UUIDModel, TimestampMixin


class TemplateCreate(BaseModel):
    category: str = Field(...)  # research, distribution, tonality, trigger_library
    name: str = Field(..., min_length=2, max_length=255)
    content: dict = {}
    is_default: bool = False
    parent_id: UUID | None = None


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    content: dict | None = None
    is_default: bool | None = None


class TemplateRead(UUIDModel):
    category: str
    name: str
    owner_id: str | None = None
    is_default: bool = False
    content: dict = {}
    version: int = 1
    parent_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
