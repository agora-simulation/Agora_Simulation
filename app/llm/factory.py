"""
Provider-Factory: Liefert einen LLMProvider auf Basis eines Namens
oder eines Registry-Eintrags. Singleton-Cache pro Prozess.
"""
import logging
from typing import TYPE_CHECKING

from app.llm.provider import LLMProvider

if TYPE_CHECKING:
    from app.models.provider import LLMProviderRegistry

logger = logging.getLogger("simulator.llm.factory")

# Legacy-Cache (env-basierte Provider)
_cache: dict[str, LLMProvider] = {}

# Registry-Cache (DB-basierte Provider, Key = UUID als String)
_registry_cache: dict[str, LLMProvider] = {}


def get_provider(name: str | None = None) -> LLMProvider:
    """Liefert einen LLMProvider aus den ENV-Settings. None / unbekannt → Default 'anthropic'."""
    key = (name or "anthropic").lower().strip()
    if key not in ("anthropic", "openai"):
        logger.warning("Unbekannter Provider '%s' — fallback auf 'anthropic'", key)
        key = "anthropic"

    if key in _cache:
        return _cache[key]

    if key == "anthropic":
        from app.llm.anthropic_impl import build_default_provider
        provider = build_default_provider()
    else:  # "openai"
        from app.llm.openai_impl import build_default_provider
        provider = build_default_provider()

    _cache[key] = provider
    return provider


def get_provider_by_registry(entry: "LLMProviderRegistry") -> LLMProvider:
    """Baut einen LLMProvider aus einem DB-Registry-Eintrag. Cached per UUID."""
    cache_key = str(entry.id)
    if cache_key in _registry_cache:
        return _registry_cache[cache_key]

    from app.utils.crypto import decrypt_api_key

    api_key = decrypt_api_key(entry.api_key_encrypted)
    provider_type = entry.provider_type

    if provider_type == "anthropic":
        from app.llm.anthropic_impl import AnthropicProvider
        provider = AnthropicProvider(api_key=api_key)
    elif provider_type == "openai":
        from app.llm.openai_impl import OpenAIProvider
        from app.config import settings
        provider = OpenAIProvider(
            api_key=api_key,
            model_fast=settings.openai_model_fast,
            model_smart=settings.openai_model_smart,
        )
    elif provider_type == "ollama":
        from app.llm.ollama_impl import OllamaProvider
        provider = OllamaProvider(
            base_url=entry.base_url or "http://localhost:11434/v1",
        )
    else:
        raise RuntimeError(f"Unbekannter Provider-Typ in Registry: {provider_type}")

    _registry_cache[cache_key] = provider
    return provider
