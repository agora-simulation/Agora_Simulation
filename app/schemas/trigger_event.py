"""Pydantic schemas for Trigger Events (v1.1)."""
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import UUIDModel, TimestampMixin


class TriggerEventCreate(BaseModel):
    simulation_id: UUID
    tick_day: int = Field(..., ge=1)
    event_type: str = Field(...)  # news_headline, competitor_action, regulatory_change, validator_decision, social_incident
    title: str = Field(..., min_length=5, max_length=500)
    content: str | None = None
    affected_segments: list[str] = []
    intensity: str = Field("minor")  # minor, major, critical
    source_attribution: str | None = None


class TriggerEventRead(UUIDModel, TimestampMixin):
    simulation_id: UUID
    tick_day: int
    event_type: str
    title: str
    content: str | None = None
    affected_segments: list[str] = []
    intensity: str = "minor"
    source_attribution: str | None = None
    was_auto_generated: bool = False
