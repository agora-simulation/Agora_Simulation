"""Pydantic schemas for Research Snapshots (v1.2 — with execution support)."""
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
    provider_id: UUID | None = None
    model: str | None = None
    prompt: str | None = None
    system_prompt: str | None = None
    template_id: UUID | None = None
    temperature: float | None = None
    max_tokens: int = 4096


class ResearchSnapshotUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    status: str | None = None
    prompt: str | None = None
    system_prompt: str | None = None
    provider_id: UUID | None = None
    model: str | None = None
    template_id: UUID | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    passes: dict | None = None
    suggested_triggers: list | None = None


class ResearchSnapshotRead(UUIDModel, TimestampMixin):
    name: str
    owner_id: str | None = None
    provider_id: UUID | None = None
    model: str | None = None
    llm_used: str | None = None
    prompt: str | None = None
    system_prompt: str | None = None
    result: str | None = None
    template_id: UUID | None = None
    temperature: float | None = None
    max_tokens: int = 4096
    passes: dict = {}
    status: str = "draft"
    suggested_triggers: list = []
    error: str | None = None
    execution_started_at: datetime | None = None
    execution_finished_at: datetime | None = None
    updated_at: datetime | None = None


class ResearchExecuteRequest(BaseModel):
    """Optional overrides when triggering execution."""
    prompt: str | None = None
    system_prompt: str | None = None
    provider_id: UUID | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
