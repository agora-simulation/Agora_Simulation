"""
Provider-Resolver: Wählt für eine Simulationsphase den passenden Provider
und gibt alle Sampling-Parameter zurück.

Unterstützt:
- Neues `provider_config` JSON (Multi-Provider mit Gewichtung)
- Legacy-Fallback auf `llm_provider` + `llm_model_fast/smart` Spalten
"""
import logging
import random
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.factory import get_provider, get_provider_by_registry
from app.llm.provider import LLMProvider
from app.models.provider import LLMProviderRegistry

logger = logging.getLogger("simulator.llm.resolver")

Phase = Literal["persona_generation", "agent_actions", "state_updates", "analysis_reports"]


@dataclass
class ResolvedProvider:
    """Ergebnis der Provider-Auflösung für einen einzelnen Call."""
    provider: LLMProvider
    model: str | None
    temperature: float | None
    top_p: float | None
    top_k: int | None


async def resolve_for_phase(
    sim: Any,
    phase: Phase,
    db: AsyncSession,
) -> ResolvedProvider:
    """Löst den Provider für eine Phase auf.

    1. Prüft ob sim.provider_config gesetzt ist (neues System)
    2. Falls ja: Weighted-Random-Selection aus den Phase-Einträgen
    3. Falls nein: Legacy-Fallback auf llm_provider + llm_model_*
    """
    provider_config = getattr(sim, "provider_config", None)

    if provider_config and isinstance(provider_config, dict):
        phase_cfg = provider_config.get(phase)
        if phase_cfg and isinstance(phase_cfg, dict):
            entries = phase_cfg.get("entries", [])
            if entries:
                return await _resolve_from_entries(entries, db)

    # Legacy-Fallback
    return _resolve_legacy(sim, phase)


async def _resolve_from_entries(
    entries: list[dict],
    db: AsyncSession,
) -> ResolvedProvider:
    """Weighted-Random-Selection aus Provider-Config-Einträgen."""
    weights = [e.get("weight", 100) for e in entries]
    selected = random.choices(entries, weights=weights, k=1)[0]

    provider_id = selected.get("provider_id")
    if not provider_id:
        raise RuntimeError("provider_config entry ohne provider_id")

    # Provider aus Registry laden
    registry_entry = await db.get(LLMProviderRegistry, provider_id)
    if not registry_entry:
        raise RuntimeError(f"Provider {provider_id} nicht in Registry gefunden")

    provider = get_provider_by_registry(registry_entry)

    return ResolvedProvider(
        provider=provider,
        model=selected.get("model"),
        temperature=selected.get("temperature"),
        top_p=selected.get("top_p"),
        top_k=selected.get("top_k"),
    )


def _resolve_legacy(sim: Any, phase: Phase) -> ResolvedProvider:
    """Legacy-Fallback: ein Provider, kein Sampling-Override."""
    provider_name = getattr(sim, "llm_provider", None)
    provider = get_provider(provider_name)

    # Modell-Override basierend auf Phase-Tier
    if phase in ("persona_generation", "analysis_reports"):
        model = getattr(sim, "llm_model_smart", None) or None
    else:
        model = getattr(sim, "llm_model_fast", None) or None

    return ResolvedProvider(
        provider=provider,
        model=model,
        temperature=None,
        top_p=None,
        top_k=None,
    )
