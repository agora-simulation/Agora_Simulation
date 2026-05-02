from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Provider-Registry CRUD
# ---------------------------------------------------------------------------

ProviderType = Literal["anthropic", "openai", "ollama"]


class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    provider_type: ProviderType
    api_key: str = Field(..., min_length=1, max_length=2048)
    base_url: str | None = Field(None, max_length=2048)
    is_default: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    api_key: str | None = Field(None, min_length=1, max_length=2048)
    base_url: str | None = None
    is_default: bool | None = None


class ProviderRead(BaseModel):
    id: UUID
    name: str
    provider_type: str
    base_url: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Per-Phase Provider-Konfiguration (für Simulationen)
# ---------------------------------------------------------------------------

class PhaseProviderEntry(BaseModel):
    """Ein Provider-Slot innerhalb einer Phase."""
    provider_id: UUID
    model: str = Field(..., max_length=64)
    weight: int = Field(100, ge=1)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    top_k: int | None = Field(None, ge=1)


class PhaseConfig(BaseModel):
    """Konfiguration einer einzelnen Simulationsphase."""
    entries: list[PhaseProviderEntry] = Field(..., min_length=1)


class SimulationProviderConfig(BaseModel):
    """Vollständige Provider-Konfiguration für alle 4 Phasen einer Simulation."""
    persona_generation: PhaseConfig
    agent_actions: PhaseConfig
    state_updates: PhaseConfig
    analysis_reports: PhaseConfig
    preset: str | None = None


# ---------------------------------------------------------------------------
# Kostenvorschau
# ---------------------------------------------------------------------------

class CostEstimateRequest(BaseModel):
    persona_count: int = Field(..., ge=1, le=10000)
    tick_count: int = Field(..., ge=1, le=1000)
    provider_config: SimulationProviderConfig


class PhaseBreakdown(BaseModel):
    calls: int
    estimated_usd: float


class CostEstimateResponse(BaseModel):
    total_estimated_usd: float
    breakdown: dict[str, PhaseBreakdown]
    per_provider: dict[str, float]


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

class PresetPhaseInfo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_tier: str
    temperature: float


class PresetInfo(BaseModel):
    id: str
    label: str
    description: str
    persona_generation: PresetPhaseInfo
    agent_actions: PresetPhaseInfo
    state_updates: PresetPhaseInfo
    analysis_reports: PresetPhaseInfo
