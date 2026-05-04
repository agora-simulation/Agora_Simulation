"""Pydantic schemas for Platform Layer (v1.1)."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import UUIDModel


class PlatformCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    character: str = Field(..., max_length=50)
    tonality_modifier: str | None = None
    reach_multiplier: float = Field(1.0, ge=0.1, le=10.0)
    preferred_actor_types: list[str] = []
    echo_chamber_strength: float = Field(0.5, ge=0, le=1)
    default_engagement_rate: float = Field(0.3, ge=0, le=1)
    simulation_id: UUID | None = None


class PlatformUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    character: str | None = Field(None, max_length=50)
    tonality_modifier: str | None = None
    reach_multiplier: float | None = Field(None, ge=0.1, le=10.0)
    preferred_actor_types: list[str] | None = None
    echo_chamber_strength: float | None = Field(None, ge=0, le=1)
    default_engagement_rate: float | None = Field(None, ge=0, le=1)
    is_active: bool | None = None


class PlatformRead(UUIDModel):
    simulation_id: UUID | None = None
    name: str
    character: str
    tonality_modifier: str | None = None
    reach_multiplier: float = 1.0
    preferred_actor_types: list[str] = []
    echo_chamber_strength: float = 0.5
    default_engagement_rate: float = 0.3
    is_active: bool = True
    created_at: datetime | None = None
