"""
Webhook-Dispatcher.
Sendet HTTP-POST an die konfigurierte URL wenn eine Simulation endet.
"""
import logging
from uuid import UUID

import httpx

logger = logging.getLogger("agora.webhooks")

WEBHOOK_TIMEOUT = 10.0  # Sekunden


async def dispatch_webhook(
    webhook_url: str,
    simulation_id: UUID,
    status: str,
    current_tick: int,
    total_ticks: int,
) -> None:
    """
    Sendet eine Webhook-Notification. Fehler werden geloggt aber nicht propagiert
    — ein fehlgeschlagener Webhook darf die Simulation nicht als failed markieren.
    """
    payload = {
        "event": "simulation.completed" if status == "completed" else "simulation.failed",
        "simulation_id": str(simulation_id),
        "status": status,
        "current_tick": current_tick,
        "total_ticks": total_ticks,
    }

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json", "User-Agent": "SimulationsEngine/0.1"},
            )
            response.raise_for_status()
            logger.info(f"Webhook gesendet an {webhook_url} — Status {response.status_code}")
    except httpx.TimeoutException:
        logger.warning(f"Webhook Timeout: {webhook_url}")
    except httpx.HTTPStatusError as e:
        logger.warning(f"Webhook HTTP-Fehler {e.response.status_code}: {webhook_url}")
    except Exception as e:
        logger.error(f"Webhook fehlgeschlagen: {webhook_url} — {e}")
