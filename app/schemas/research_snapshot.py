"""Pydantic schemas for Research Snapshots (v1.1)."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import UUIDModel, TimestampMixin


class ResearchPassResult(BaseModel):
    content: str = ""
    sources: list[str] = []
    confidence: str = "MEDIUM"


class ResearchSnapshotCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    llm_used: str | None = None
    passes: dict[str, ResearchPassResult] = {}


class ResearchSnapshotUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    status: str | None = None
    passes: dict | None = None
    suggested_triggers: list | None = None


class ResearchSnapshotRead(UUIDModel, TimestampMixin):
    name: str
    owner_id: str | None = None
    llm_used: str | None = None
    passes: dict = {}
    status: str = "draft"
    suggested_triggers: list = []
    updated_at: datetime | None = None
