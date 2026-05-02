"""
Provider-Abstraktion für LLM-Calls (Anthropic Claude oder OpenAI GPT).

Zwei Methoden reichen für alle Use-Cases der Simulation:
- call_tool(): erzwungener Tool-Use, gibt geparste Tool-Argumente zurück.
- chat(): freie Textantwort (für Persona-Chat).

Der "tier" entscheidet zwischen Fast (Haiku / gpt-4o-mini) und Smart (Sonnet / gpt-4o).
Konkrete Modellnamen werden in den Implementations festgelegt und sind über
Settings konfigurierbar.
"""
from abc import ABC, abstractmethod
from typing import Literal, TypedDict


Tier = Literal["fast", "smart"]


class UserBlock(TypedDict, total=False):
    text: str
    cache: bool  # True = Provider darf Block cachen (Anthropic ephemeral / OpenAI no-op)


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class LLMProvider(ABC):
    """Abstrakte Schnittstelle für LLM-Aufrufe."""

    name: str  # "anthropic" | "openai"

    @abstractmethod
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
        """Erzwungener Tool-Use. Liefert die geparsten Tool-Argumente.

        Wenn model gesetzt ist, wird dieses Modell verwendet; sonst der Tier-Default.
        temperature, top_p, top_k werden an den Provider weitergereicht (soweit unterstützt).
        Wirft RuntimeError, wenn der Provider keine Tool-Antwort liefert
        (z. B. weil max_tokens erreicht wurde).
        """
        ...

    @abstractmethod
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
        """Freie Textantwort eines Chat-Modells (für Persona-Chat).

        Wenn model gesetzt ist, wird dieses Modell verwendet; sonst der Tier-Default.
        temperature, top_p, top_k werden an den Provider weitergereicht (soweit unterstützt).
        Liefert reinen Antworttext (kein Tool-Use).
        """
        ...
