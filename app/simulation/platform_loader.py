"""Platform Loader: Lädt aktive Plattformen für eine Simulation aus der DB.

Zentrale Stelle die sicherstellt, dass die Simulation nur aktive Plattformen nutzt.
Fallback auf Default-Plattformen (feedbook, threadit) wenn keine konfiguriert.
"""
import logging
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import SimPlatform
from app.models.content import DEFAULT_PLATFORMS

logger = logging.getLogger("agora.platform_loader")


async def load_active_platforms(
    simulation_id: UUID,
    db: AsyncSession,
) -> list[dict]:
    """Lädt alle aktiven Plattformen für eine Simulation.

    Berücksichtigt:
    - Globale Plattformen (simulation_id=NULL, is_active=True)
    - Simulations-spezifische Plattformen (simulation_id=X, is_active=True)

    Returns:
        Liste von Platform-Dicts mit allen relevanten Feldern.
        Fallback: Default-Plattformen wenn keine aktiven gefunden.
    """
    result = await db.execute(
        select(SimPlatform)
        .where(
            or_(
                SimPlatform.simulation_id == simulation_id,
                SimPlatform.simulation_id.is_(None),
            )
        )
        .where(SimPlatform.is_active.is_(True))
        .order_by(SimPlatform.name)
    )
    platforms = result.scalars().all()

    if not platforms:
        logger.info(f"[{simulation_id}] Keine aktiven SimPlatforms — verwende Defaults")
        return [
            {
                "name": "feedbook",
                "character": "boulevard",
                "tonality_modifier": None,
                "reach_multiplier": 1.0,
                "preferred_actor_types": [],
                "echo_chamber_strength": 0.5,
                "default_engagement_rate": 0.3,
            },
            {
                "name": "threadit",
                "character": "fachlich",
                "tonality_modifier": None,
                "reach_multiplier": 1.0,
                "preferred_actor_types": [],
                "echo_chamber_strength": 0.4,
                "default_engagement_rate": 0.4,
            },
        ]

    loaded = []
    for p in platforms:
        loaded.append({
            "id": str(p.id),
            "name": p.name,
            "character": p.character,
            "tonality_modifier": p.tonality_modifier,
            "reach_multiplier": p.reach_multiplier or 1.0,
            "preferred_actor_types": p.preferred_actor_types or [],
            "echo_chamber_strength": p.echo_chamber_strength or 0.5,
            "default_engagement_rate": p.default_engagement_rate or 0.3,
        })

    logger.info(
        f"[{simulation_id}] {len(loaded)} aktive Plattformen geladen: "
        f"{[p['name'] for p in loaded]}"
    )
    return loaded


def get_platform_names(platforms: list[dict]) -> list[str]:
    """Extrahiert Plattform-Namen für Tool-Schemas."""
    return [p["name"] for p in platforms]


def build_platform_affinity(platforms: list[dict], preferred: str | None = None) -> dict[str, float]:
    """Baut initiale Platform-Affinity basierend auf aktiven Plattformen.

    Args:
        platforms: Liste aktiver Platform-Dicts
        preferred: Name der bevorzugten Plattform (optional)

    Returns:
        Dict {platform_name: affinity_value}
    """
    n = len(platforms)
    if n == 0:
        return {"feedbook": 0.5, "threadit": 0.5}

    # Gleichmäßig verteilen, bevorzugte Plattform boosten
    base = 1.0 / n
    affinity = {}
    for p in platforms:
        name = p["name"]
        if name == preferred:
            affinity[name] = min(1.0, base * 2.0)
        else:
            affinity[name] = base

    # Normalisieren (Summe = 1.0)
    total = sum(affinity.values())
    if total > 0:
        affinity = {k: round(v / total, 3) for k, v in affinity.items()}

    return affinity


def get_platform_by_name(platforms: list[dict], name: str) -> dict | None:
    """Findet eine Plattform nach Name."""
    for p in platforms:
        if p["name"] == name:
            return p
    return None
