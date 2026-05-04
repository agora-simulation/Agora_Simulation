"""Pydantic schemas for Crowd Layer (v1.1)."""
from uuid import UUID
from app.schemas.common import UUIDModel, TimestampMixin


class CrowdStateRead(UUIDModel, TimestampMixin):
    simulation_id: UUID
    platform_id: UUID | None = None
    tick: int
    volume: int = 0
    sentiment: float = 0.0
    polarization: float = 0.0
    momentum: float = 0.0
    representative_voices: list[str] = []
