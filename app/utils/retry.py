"""
Exponential Backoff Retry-Decorator für async Funktionen.
Speziell auf Anthropic API-Fehler ausgelegt.
"""
import asyncio
import logging
from typing import Callable, TypeVar

import anthropic

logger = logging.getLogger("agora.retry")

T = TypeVar("T")

async def with_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs,
):
    """
    Führt func mit Exponential Backoff aus.

    Retry bei:
    - anthropic.RateLimitError (429) — immer retry
    - anthropic.InternalServerError (500) — retry
    - anthropic.APIConnectionError — retry

    Kein Retry bei:
    - anthropic.AuthenticationError (401) — Konfigurationsfehler
    - anthropic.BadRequestError (400) — Prompt-Problem
    - Alle anderen Exceptions — nicht retrybar
    """
    retryable = (
        anthropic.RateLimitError,
        anthropic.InternalServerError,
        anthropic.APIConnectionError,
    )

    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except retryable as e:
            last_exc = e
            if attempt == max_attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                f"Anthropic API Fehler ({type(e).__name__}), "
                f"Versuch {attempt}/{max_attempts}, warte {delay:.1f}s: {e}"
            )
            await asyncio.sleep(delay)
        except Exception:
            raise  # Nicht retrybar — sofort propagieren

    raise last_exc
