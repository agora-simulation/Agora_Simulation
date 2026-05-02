"""
Anthropic Claude Implementation des LLMProvider-Interfaces.

Mapping:
- tier="fast"  → claude-haiku-4-5-20251001
- tier="smart" → claude-sonnet-4-6

Caching via cache_control: ephemeral wird unterstützt, sowohl auf System-Prompt
als auch auf einzelnen User-Blöcken (cache=True).
"""
import asyncio
import logging
from typing import Any

import anthropic

from app.config import settings
from app.llm.provider import ChatMessage, LLMProvider, Tier, UserBlock

logger = logging.getLogger("agora.llm.anthropic")

_RETRYABLE = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model_fast: str = "claude-haiku-4-5-20251001",
        model_smart: str = "claude-sonnet-4-6",
    ):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model_fast = model_fast
        self._model_smart = model_smart

    def _resolve_model(self, tier: Tier, override: str | None) -> str:
        if override:
            return override
        return self._model_fast if tier == "fast" else self._model_smart

    async def _retry(self, fn, *args, max_attempts: int = 3, base_delay: float = 1.0, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return await fn(*args, **kwargs)
            except _RETRYABLE as e:
                last_exc = e
                if attempt == max_attempts:
                    break
                delay = min(base_delay * (2 ** (attempt - 1)), 30.0)
                logger.warning(
                    "Anthropic %s, Versuch %d/%d, warte %.1fs: %s",
                    type(e).__name__, attempt, max_attempts, delay, e,
                )
                await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    def _build_user_content(self, user_blocks: list[UserBlock]) -> list[dict]:
        out: list[dict] = []
        for block in user_blocks:
            entry: dict[str, Any] = {"type": "text", "text": block.get("text", "")}
            if block.get("cache"):
                entry["cache_control"] = {"type": "ephemeral"}
            out.append(entry)
        return out

    def _sampling_kwargs(
        self, temperature: float | None, top_p: float | None, top_k: int | None,
    ) -> dict[str, Any]:
        """Baut optionale Sampling-Parameter für die Anthropic API.

        Neuere Claude-Modelle (4.x) akzeptieren temperature/top_p/top_k nicht
        mehr — diese Parameter werden daher nicht mehr gesendet.
        """
        if any(v is not None for v in (temperature, top_p, top_k)):
            logger.debug(
                "Sampling-Parameter ignoriert (von Claude 4.x nicht unterstützt): "
                "temperature=%s, top_p=%s, top_k=%s",
                temperature, top_p, top_k,
            )
        return {}

    async def call_tool(
        self,
        *,
        tier: Tier,
        system: str,
        cache_system: bool,
        user_blocks: list[UserBlock],
        tool_name: str,
        tool_description: str,
        tool_schema: dict,
        max_tokens: int,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> dict:
        system_payload: list[dict[str, Any]] = [{"type": "text", "text": system}]
        if cache_system:
            system_payload[0]["cache_control"] = {"type": "ephemeral"}

        tool_def = {
            "name": tool_name,
            "description": tool_description,
            "input_schema": tool_schema,
        }

        message = await self._retry(
            self._client.messages.create,
            model=self._resolve_model(tier, model),
            max_tokens=max_tokens,
            system=system_payload,
            messages=[
                {
                    "role": "user",
                    "content": self._build_user_content(user_blocks),
                }
            ],
            tools=[tool_def],
            tool_choice={"type": "tool", "name": tool_name},
            **self._sampling_kwargs(temperature, top_p, top_k),
        )

        tool_block = next((b for b in message.content if b.type == "tool_use"), None)
        if tool_block is None:
            text_blocks = [b.text for b in message.content if b.type == "text"]
            raise RuntimeError(
                f"Anthropic: keine Tool-Antwort (stop_reason={message.stop_reason}, "
                f"max_tokens={max_tokens}). Text: {' '.join(text_blocks)[:300]}"
            )
        if not isinstance(tool_block.input, dict):
            raise RuntimeError(f"Anthropic: tool_block.input ist kein dict ({type(tool_block.input)})")
        return tool_block.input

    async def chat(
        self,
        *,
        tier: Tier,
        system: str,
        messages: list[ChatMessage],
        max_tokens: int,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> str:
        response = await self._retry(
            self._client.messages.create,
            model=self._resolve_model(tier, model),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            **self._sampling_kwargs(temperature, top_p, top_k),
        )
        # Erster Text-Block
        for block in response.content:
            if block.type == "text":
                return block.text
        raise RuntimeError(f"Anthropic chat: keine Text-Antwort (stop_reason={response.stop_reason})")


def build_default_provider() -> AnthropicProvider:
    """Baut den Default-Anthropic-Provider aus Settings."""
    return AnthropicProvider(
        api_key=settings.anthropic_api_key,
        model_fast=getattr(settings, "anthropic_model_fast", "claude-haiku-4-5-20251001"),
        model_smart=getattr(settings, "anthropic_model_smart", "claude-sonnet-4-6"),
    )
