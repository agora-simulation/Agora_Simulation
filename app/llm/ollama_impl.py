"""
Ollama Implementation des LLMProvider-Interfaces.

Nutzt die OpenAI-kompatible API von Ollama (localhost:11434/v1).
"""
import asyncio
import json
import logging

from app.llm.provider import ChatMessage, LLMProvider, Tier, UserBlock

logger = logging.getLogger("simulator.llm.ollama")


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434/v1",
        model_fast: str = "qwen2.5:7b",
        model_smart: str = "qwen2.5:7b",
    ):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key="ollama", base_url=base_url)
        self._model_fast = model_fast
        self._model_smart = model_smart

        import openai as _openai
        self._retryable = (
            _openai.APIConnectionError,
            _openai.InternalServerError,
        )

    def _resolve_model(self, tier: Tier, override: str | None) -> str:
        if override:
            return override
        return self._model_fast if tier == "fast" else self._model_smart

    def _sampling_kwargs(
        self, temperature: float | None, top_p: float | None, top_k: int | None,
    ) -> dict:
        kw: dict = {}
        if temperature is not None:
            kw["temperature"] = temperature
        if top_p is not None:
            kw["top_p"] = top_p
        # top_k via extra_body für Ollama
        if top_k is not None:
            kw["extra_body"] = {"top_k": top_k}
        return kw

    async def _retry(self, fn, *args, max_attempts: int = 3, base_delay: float = 1.0, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return await fn(*args, **kwargs)
            except self._retryable as e:
                last_exc = e
                if attempt == max_attempts:
                    break
                delay = min(base_delay * (2 ** (attempt - 1)), 30.0)
                logger.warning(
                    "Ollama %s, Versuch %d/%d, warte %.1fs: %s",
                    type(e).__name__, attempt, max_attempts, delay, e,
                )
                await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _merge_user_blocks(blocks: list[UserBlock]) -> str:
        return "\n\n".join(b.get("text", "") for b in blocks if b.get("text"))

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
        user_text = self._merge_user_blocks(user_blocks)
        resolved_model = self._resolve_model(tier, model)

        function_def = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": tool_schema,
            },
        }

        response = await self._retry(
            self._client.chat.completions.create,
            model=resolved_model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            tools=[function_def],
            tool_choice={"type": "function", "function": {"name": tool_name}},
            **self._sampling_kwargs(temperature, top_p, top_k),
        )

        choice = response.choices[0]
        tool_calls = choice.message.tool_calls or []
        if not tool_calls:
            text = choice.message.content or ""
            raise RuntimeError(
                f"Ollama: keine Tool-Antwort (finish_reason={choice.finish_reason}). "
                f"Text: {text[:300]}"
            )

        raw_args = tool_calls[0].function.arguments or "{}"
        try:
            parsed = json.loads(raw_args)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Ollama: Tool-Argumente nicht parsebar: {e}. Raw: {raw_args[:300]}")

        if not isinstance(parsed, dict):
            raise RuntimeError(f"Ollama: Tool-Argumente sind kein dict ({type(parsed)})")
        return parsed

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
        resolved_model = self._resolve_model(tier, model)

        payload: list[dict] = [{"role": "system", "content": system}]
        payload.extend({"role": m["role"], "content": m["content"]} for m in messages)

        response = await self._retry(
            self._client.chat.completions.create,
            model=resolved_model,
            max_completion_tokens=max_tokens,
            messages=payload,
            **self._sampling_kwargs(temperature, top_p, top_k),
        )

        text = response.choices[0].message.content
        if not text:
            raise RuntimeError(
                f"Ollama chat: keine Text-Antwort (finish_reason={response.choices[0].finish_reason})"
            )
        return text
