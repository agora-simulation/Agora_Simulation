from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.simulation import SimulationStatus
from app.schemas.common import UUIDModel, TimestampMixin
from app.schemas.provider import SimulationProviderConfig

LLMProviderName = Literal["anthropic", "openai", "ollama"]
ResearchMode = Literal["quick", "deep"]


class SimulationConfig(BaseModel):
    persona_count: int = Field(10, ge=2, le=500)
    tick_count: int = Field(15, ge=1, le=100)


class SimulationCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    product_description: str = Field(..., min_length=20, max_length=10000)
    target_market: str | None = Field(None, max_length=255)
    industry: str | None = Field(None, max_length=255)
    config: SimulationConfig = SimulationConfig()
    webhook_url: str | None = None
    llm_provider: LLMProviderName = "anthropic"
    llm_model_fast: str | None = Field(None, max_length=64)
    llm_model_smart: str | None = Field(None, max_length=64)
    provider_config: SimulationProviderConfig | None = None
    research_mode: ResearchMode = Field("quick", description="'quick' = ohne Web-Recherche, 'deep' = mit Web-Recherche vor Persona-Generierung")
    # v1.1
    research_snapshot_id: UUID | None = None
    stagnation_mode: str = Field("mild", description="off, mild, aggressive")
    distribution_template: dict | None = None

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v):
        if v is None:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("webhook_url muss mit http:// oder https:// beginnen")
        if len(v) > 2048:
            raise ValueError("webhook_url darf maximal 2048 Zeichen lang sein")
        return v

    @field_validator("name")
    @classmethod
    def strip_name(cls, v):
        return v.strip()

    @field_validator("product_description")
    @classmethod
    def strip_description(cls, v):
        return v.strip()


class SimulationRead(UUIDModel, TimestampMixin):
    name: str
    product_description: str
    target_market: str | None
    industry: str | None
    status: SimulationStatus
    current_tick: int
    total_ticks: int
    config: dict
    updated_at: datetime
    webhook_url: str | None
    llm_provider: str = "anthropic"
    llm_model_fast: str | None = None
    llm_model_smart: str | None = None
    provider_config: dict | None = None
    run_group_id: UUID | None = None
    run_index: int | None = None
    research_mode: str = "quick"
    # v1.1
    research_snapshot_id: UUID | None = None
    stagnation_mode: str = "mild"
    distribution_template: dict | None = None


class SimulationRunResponse(BaseModel):
    simulation_id: UUID
    status: str
    message: str


class SimulationStats(BaseModel):
    """Detaillierter Status einer Simulation."""
    simulation_id: UUID
    status: SimulationStatus
    current_tick: int
    total_ticks: int
    progress_pct: int
    persona_count: int
    post_count: int
    comment_count: int
    reaction_count: int


class SimulationResetResponse(BaseModel):
    simulation_id: UUID
    message: str


class MultiRunRequest(BaseModel):
    """Konfiguration für Multi-Run-Simulationen."""
    run_count: int = Field(3, ge=2, le=5, description="Anzahl paralleler Runs (2-5)")


class MultiRunResponse(BaseModel):
    """Antwort auf Multi-Run-Start."""
    run_group_id: UUID
    simulation_ids: list[UUID]
    run_count: int
    message: str


class MarketContextRead(BaseModel):
    """Market Context Document aus der Web-Recherche."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    simulation_id: UUID
    macro_context: str | None
    industry_context: str | None
    target_group_context: str | None
    prompt_summary: str | None
    raw_sources: list | None = None
    research_queries: list | None = None
    research_mode: str = "deep"
    created_at: datetime | None = None


class MarketContextUpdate(BaseModel):
    """Manuelles Update des Market Context."""
    macro_context: str | None = None
    industry_context: str | None = None
    target_group_context: str | None = None
    prompt_summary: str | None = None


class MultiRunComparisonResponse(BaseModel):
    """Vergleichs-Report über mehrere Runs."""
    run_group_id: UUID
    run_count: int
    completed_runs: int
    convergence_consistency: dict
    sentiment_bandwidth: dict
    dimension_variance: dict
    confidence_scores: dict
    narrative_stability: str
    recommendation: str
