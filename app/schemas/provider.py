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


# ---------------------------------------------------------------------------
# Provider Capabilities & Model Discovery
# ---------------------------------------------------------------------------

class ParamCapability(BaseModel):
    """Beschreibt ob ein Parameter unterstützt wird und ggf. Einschränkungen."""
    supported: bool
    default: float | int | None = None
    min: float | int | None = None
    max: float | int | None = None
    reason: str | None = None  # Warum nicht unterstützt / Einschränkung


class ModelCapabilities(BaseModel):
    """Capabilities eines spezifischen Modells."""
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    label: str
    tier: str  # "fast" | "smart"
    provider_type: ProviderType
    temperature: ParamCapability
    top_p: ParamCapability
    top_k: ParamCapability
    system_prompt: ParamCapability
    caching: ParamCapability
    max_output_tokens: int
    pricing_input_per_1m: float  # USD pro 1M Input-Tokens
    pricing_output_per_1m: float  # USD pro 1M Output-Tokens


class ProviderCapabilities(BaseModel):
    """Alle Capabilities eines Provider-Typs."""
    provider_type: ProviderType
    display_name: str
    models: list[ModelCapabilities]
    supports_api_key: bool = True
    supports_base_url: bool = False
    notes: list[str] = []


class DiscoveredModel(BaseModel):
    """Ein Modell das via API-Discovery gefunden wurde (z.B. Ollama)."""
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    label: str
    size: str | None = None  # z.B. "7B", "70B"
