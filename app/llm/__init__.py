"""LLM-Provider-Abstraktion (Anthropic + OpenAI + Ollama)."""
from typing import Any

from app.llm.factory import get_provider, get_provider_by_registry
from app.llm.provider import ChatMessage, LLMProvider, Tier, UserBlock
from app.llm.resolver import ResolvedProvider, resolve_for_phase


def resolve_model(sim: Any, tier: Tier) -> str | None:
    """Liest sim.llm_model_fast / llm_model_smart und liefert den Override (oder None).

    sim ist optional — wenn None, gibt None zurück (Tier-Default greift).
    Legacy-Helper — neuer Code sollte resolve_for_phase() nutzen.
    """
    if sim is None:
        return None
    if tier == "fast":
        return getattr(sim, "llm_model_fast", None) or None
    return getattr(sim, "llm_model_smart", None) or None


__all__ = [
    "LLMProvider", "Tier", "UserBlock", "ChatMessage",
    "get_provider", "get_provider_by_registry", "resolve_model",
    "ResolvedProvider", "resolve_for_phase",
]
