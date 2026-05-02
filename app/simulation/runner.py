"""
Simulation Runner — Background Task Orchestrator.
Öffnet eigene DB-Session (unabhängig vom Request-Lifecycle).
"""
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, func

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Simulation, SimulationStatus, Persona
from app.simulation.persona_generator import generate_personas
from app.simulation.tick_engine import run_tick
from app.analysis.report_generator import generate_report
from app.webhooks import dispatch_webhook
from app.llm.resolver import resolve_for_phase

logger = logging.getLogger("simulator.runner")

# Globaler Semaphore — max concurrent Anthropic API Calls (aus Settings)
semaphore = asyncio.Semaphore(settings.default_agent_concurrent_calls)


async def reset_stale_simulations() -> int:
    """
    Setzt Simulationen die beim Server-Start noch 'running' sind auf 'failed'.
    Wird beim App-Startup aufgerufen.
    Gibt die Anzahl der zurückgesetzten Simulationen zurück.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Simulation)
            .where(Simulation.status == SimulationStatus.running)
            .values(status=SimulationStatus.failed, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
            .returning(Simulation.id)
        )
        stale_ids = result.fetchall()
        await db.commit()
        if stale_ids:
            logger.warning(f"Stale Simulationen beim Start zurückgesetzt: {len(stale_ids)}")
        return len(stale_ids)


async def _assign_social_connections(db, simulation_id: UUID):
    """Weist jeder Persona homophilie-basierte Verbindungen zu (3-8 andere Personas).

    Ähnliche Personas werden mit höherer Wahrscheinlichkeit verbunden:
    - Gleiche Stadt: +3
    - Ähnliches Alter (±10 Jahre): +2
    - Gemeinsame Values: +1 pro geteiltem Wert
    - Gleicher Skeptiker-Status: +1
    """
    import random

    result = await db.execute(
        select(Persona).where(Persona.simulation_id == simulation_id)
    )
    personas = result.scalars().all()
    persona_ids = [str(p.id) for p in personas]

    def _similarity_score(a: Persona, b: Persona) -> float:
        score = 0.0
        # Gleiche Stadt
        if a.location and b.location and a.location.strip().lower() == b.location.strip().lower():
            score += 3
        # Ähnliches Alter (±10 Jahre)
        try:
            age_a = int(a.age)
            age_b = int(b.age)
            if abs(age_a - age_b) <= 10:
                score += 2
        except (ValueError, TypeError):
            pass
        # Gemeinsame Values
        values_a = set(v.lower() for v in (a.values or []))
        values_b = set(v.lower() for v in (b.values or []))
        score += len(values_a & values_b)
        # Gleicher Skeptiker-Status (Echokammer-Effekt)
        if a.is_skeptic == b.is_skeptic:
            score += 1
        return score

    for persona in personas:
        n_connections = random.randint(3, min(8, len(personas) - 1))
        others = [p for p in personas if str(p.id) != str(persona.id)]

        # Similarity-Scores berechnen
        scores = [_similarity_score(persona, other) for other in others]

        # Gewichtete Auswahl: Score + 1 als Gewicht (damit Score=0 nicht ausgeschlossen wird)
        weights = [s + 1.0 for s in scores]

        # Gewichtetes Sampling ohne Zurücklegen
        chosen_ids = []
        available = list(zip(others, weights))
        for _ in range(min(n_connections, len(available))):
            total = sum(w for _, w in available)
            r = random.uniform(0, total)
            cumulative = 0.0
            for i, (other, weight) in enumerate(available):
                cumulative += weight
                if cumulative >= r:
                    chosen_ids.append(str(other.id))
                    available.pop(i)
                    break

        persona.social_connections = chosen_ids

    await db.flush()


async def run_simulation_background(simulation_id: UUID):
    """
    Haupt-Orchestrator der Simulation.
    Wird als FastAPI BackgroundTask gestartet.
    Öffnet eigene Session — niemals Session aus Request-Context verwenden.
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"[{simulation_id}] Simulation gestartet")
            sim = await db.get(Simulation, simulation_id)

            # Max Concurrent Simulations prüfen
            running_count_result = await db.execute(
                select(func.count(Simulation.id)).where(Simulation.status == SimulationStatus.running)
            )
            running_count = running_count_result.scalar()
            if running_count > settings.max_concurrent_simulations:
                logger.warning(f"[{simulation_id}] Max concurrent simulations ({settings.max_concurrent_simulations}) erreicht")
                await db.execute(
                    update(Simulation).where(Simulation.id == simulation_id)
                    .values(status=SimulationStatus.failed, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                )
                await db.commit()
                return

            # 1. Personas generieren falls noch nicht vorhanden
            result = await db.execute(
                select(Persona).where(Persona.simulation_id == simulation_id)
            )
            existing_personas = result.scalars().all()

            if not existing_personas:
                persona_count = sim.config.get("persona_count", 10) if sim.config else 10
                raw_personas = await generate_personas(
                    product_description=sim.product_description,
                    target_market=sim.target_market or "",
                    industry=sim.industry or "",
                    persona_count=persona_count,
                    sim=sim,
                    db=db,
                )
                logger.info(f"[{simulation_id}] {len(raw_personas)} Personas generiert")
                for p_data in raw_personas:
                    # Nur bekannte Felder übernehmen
                    allowed = {
                        "name", "age", "location", "occupation", "personality",
                        "values", "communication_style", "initial_opinion", "is_skeptic",
                        # Modul 3: Erweiterte Felder
                        "education_level", "income_bracket", "family_status",
                        "political_leaning", "media_consumption", "tech_affinity",
                        "personality_traits",
                        # Entity-Typen
                        "persona_type", "entity_subtype",
                    }
                    clean = {k: v for k, v in p_data.items() if k in allowed}

                    # Initiale Plattform-Affinität aus preferred_platform ableiten
                    preferred = p_data.get("preferred_platform", "feedbook")
                    if preferred == "threadit":
                        initial_affinity = {"feedbook": 0.3, "threadit": 0.7}
                    else:
                        initial_affinity = {"feedbook": 0.7, "threadit": 0.3}

                    # Modul 2: Initiale Opinion-Dimensions
                    from app.simulation.tick_engine import _init_opinion_dimensions
                    initial_dims = _init_opinion_dimensions(clean.get("is_skeptic", False))

                    persona = Persona(
                        simulation_id=simulation_id,
                        current_state={
                            "platform_affinity": initial_affinity,
                            "opinion_dimensions": initial_dims,
                        },
                        extra={"preferred_platform": preferred},
                        **clean,
                    )
                    db.add(persona)

                await db.flush()
                await _assign_social_connections(db, simulation_id)
                await db.commit()

            # 2. Tick-Schleife
            sim = await db.get(Simulation, simulation_id)
            start_tick = (sim.current_tick or 0) + 1
            total_ticks = sim.total_ticks or 15

            for tick_num in range(start_tick, total_ticks + 1):
                # Cancellation-Check
                sim_check = await db.get(Simulation, simulation_id)
                if sim_check.status != SimulationStatus.running:
                    logger.info(f"[{simulation_id}] Simulation abgebrochen (Status: {sim_check.status.value})")
                    return

                # Pro Tick neu resolven (Multi-Provider Weighted-Random)
                action_resolved = await resolve_for_phase(sim, "agent_actions", db)
                state_resolved = await resolve_for_phase(sim, "state_updates", db)

                logger.info(f"[{simulation_id}] Tick {tick_num}/{total_ticks} gestartet")
                await run_tick(
                    simulation_id, tick_num, tick_num, db, semaphore,
                    action_resolved=action_resolved,
                    state_resolved=state_resolved,
                )

                await db.execute(
                    update(Simulation)
                    .where(Simulation.id == simulation_id)
                    .values(current_tick=tick_num, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                )
                await db.commit()
                logger.info(f"[{simulation_id}] Tick {tick_num} abgeschlossen")

            # 3. Abschluss (Report wird manuell über POST /analysis/{id}/generate ausgelöst)
            await db.execute(
                update(Simulation)
                .where(Simulation.id == simulation_id)
                .values(status=SimulationStatus.completed, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
            )
            await db.commit()
            logger.info(f"[{simulation_id}] Simulation abgeschlossen")
            if sim.webhook_url:
                await dispatch_webhook(
                    webhook_url=sim.webhook_url,
                    simulation_id=simulation_id,
                    status="completed",
                    current_tick=sim.current_tick or total_ticks,
                    total_ticks=total_ticks,
                )

        except Exception as e:
            logger.error(f"[{simulation_id}] Simulation fehlgeschlagen: {e}", exc_info=True)
            # Neue Session für den Fehler-Status (alte könnte in Rollback-State sein)
            async with AsyncSessionLocal() as err_db:
                await err_db.execute(
                    update(Simulation)
                    .where(Simulation.id == simulation_id)
                    .values(status=SimulationStatus.failed, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                )
                await err_db.commit()
            # Webhook auch bei Fehler senden
            try:
                async with AsyncSessionLocal() as webhook_db:
                    failed_sim = await webhook_db.get(Simulation, simulation_id)
                    if failed_sim and failed_sim.webhook_url:
                        await dispatch_webhook(
                            webhook_url=failed_sim.webhook_url,
                            simulation_id=simulation_id,
                            status="failed",
                            current_tick=failed_sim.current_tick or 0,
                            total_ticks=failed_sim.total_ticks or 15,
                        )
            except Exception:
                pass  # Webhook-Fehler niemals propagieren
            raise
