"""
Simulation Runner — Background Task Orchestrator.
Öffnet eigene DB-Session (unabhängig vom Request-Lifecycle).
"""
import asyncio
import logging
import random as _random
import statistics as _statistics
import uuid as _uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, func

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Simulation, SimulationStatus, Persona
from app.simulation.persona_generator import generate_personas
from app.simulation.tick_engine import run_tick
from app.simulation.platform_loader import load_active_platforms, build_platform_affinity, get_platform_names
from app.analysis.report_generator import generate_report
from app.webhooks import dispatch_webhook
from app.llm.resolver import resolve_for_phase

# v1.1 imports (lazy — models may not exist yet during migrations)
try:
    from app.models.crowd_state import CrowdState
    from app.models.trigger_event import TriggerEvent
except ImportError:
    CrowdState = None  # type: ignore[assignment,misc]
    TriggerEvent = None  # type: ignore[assignment,misc]

logger = logging.getLogger("agora.runner")

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
            .where(Simulation.status.in_([SimulationStatus.running, SimulationStatus.researching]))
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


async def _process_crowd_layer(
    simulation_id: UUID,
    ingame_day: int,
    db,
    personas: list,
    posts: list,
):
    """Processes the crowd layer for this tick.

    The crowd is a statistical aggregate, not individual personas.
    It reacts to actor posts and influences persona opinions (bandwagon effect).
    """
    if CrowdState is None:
        logger.debug("CrowdState model not available — skipping crowd layer")
        return

    from app.models.content import Post as PostModel

    # Calculate crowd metrics from today's activity
    todays_posts = [p for p in posts if p.ingame_day == ingame_day]

    if not todays_posts:
        # Minimal crowd activity even without posts
        crowd = CrowdState(
            simulation_id=simulation_id,
            tick=ingame_day,
            volume=_random.randint(5, 20),
            sentiment=0.0,
            polarization=0.0,
            momentum=0.0,
            representative_voices=["Stille Beobachtung des Marktes."],
        )
        db.add(crowd)
        return

    # Volume: based on post count and actor reach
    from app.simulation.tick_engine import ACTOR_BEHAVIOR
    total_reach = 0
    sentiment_sum = 0.0
    sentiment_count = 0

    for post in todays_posts:
        # Find author's actor type for reach multiplier
        author = next((p for p in personas if str(p.id) == str(post.author_id)), None)
        if author:
            actor_type = getattr(author, 'actor_type', 'private_person') or 'private_person'
            reach = ACTOR_BEHAVIOR.get(actor_type, ACTOR_BEHAVIOR["private_person"])["reach_mult"]
            total_reach += reach

            # Sentiment from reactions
            likes = sum(1 for r in (post.reactions or []) if r.reaction_type.value == "like")
            dislikes = sum(1 for r in (post.reactions or []) if r.reaction_type.value == "dislike")
            if likes + dislikes > 0:
                post_sentiment = (likes - dislikes) / (likes + dislikes)
                sentiment_sum += post_sentiment * reach  # Reach-weighted
                sentiment_count += reach

    volume = int(total_reach * _random.uniform(0.8, 1.2))
    sentiment = sentiment_sum / sentiment_count if sentiment_count > 0 else 0.0
    sentiment = max(-1.0, min(1.0, sentiment))

    # Polarization from persona opinions
    persona_opinions = []
    for p in personas:
        dims = (p.current_state or {}).get("opinion_dimensions", {})
        if dims:
            avg = sum(dims.values()) / len(dims)
            persona_opinions.append(avg)

    polarization = _statistics.stdev(persona_opinions) if len(persona_opinions) >= 2 else 0.0

    # Momentum: change from previous tick
    prev_crowd_result = await db.execute(
        select(CrowdState)
        .where(CrowdState.simulation_id == simulation_id)
        .where(CrowdState.tick == ingame_day - 1)
    )
    prev_crowd = prev_crowd_result.scalar_one_or_none()
    momentum = sentiment - (prev_crowd.sentiment if prev_crowd else 0.0)

    # Representative voices
    voices = []
    if sentiment > 0.3:
        voices.append("Überwiegend positive Resonanz in der Community.")
    elif sentiment < -0.3:
        voices.append("Deutliche Skepsis in der breiten Masse.")
    else:
        voices.append("Gemischte Reaktionen, keine klare Tendenz.")

    if volume > 500:
        voices.append("Hohes Diskussionsvolumen — das Thema trifft einen Nerv.")

    crowd = CrowdState(
        simulation_id=simulation_id,
        tick=ingame_day,
        volume=volume,
        sentiment=round(sentiment, 3),
        polarization=round(polarization, 3),
        momentum=round(momentum, 3),
        representative_voices=voices,
    )
    db.add(crowd)


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

            # 0. Web-Recherche (Deep Mode)
            market_context_summary = None
            research_mode = getattr(sim, "research_mode", "quick") or "quick"

            if research_mode == "deep":
                from app.models import MarketContext
                ctx_result = await db.execute(
                    select(MarketContext).where(MarketContext.simulation_id == simulation_id)
                )
                existing_ctx = ctx_result.scalar_one_or_none()

                if not existing_ctx:
                    # Recherche durchführen und danach PAUSIEREN
                    await db.execute(
                        update(Simulation).where(Simulation.id == simulation_id)
                        .values(status=SimulationStatus.researching, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                    )
                    await db.commit()

                    logger.info(f"[{simulation_id}] Deep Mode: Starte Web-Recherche")
                    try:
                        from app.research import run_market_research
                        research_resolved = await resolve_for_phase(sim, "persona_generation", db)
                        existing_ctx = await run_market_research(
                            simulation_id, db, resolved=research_resolved,
                        )
                        await db.commit()
                    except Exception as e:
                        logger.error(f"[{simulation_id}] Web-Recherche fehlgeschlagen: {e}")
                        await db.execute(
                            update(Simulation).where(Simulation.id == simulation_id)
                            .values(status=SimulationStatus.failed, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                        )
                        await db.commit()
                        return

                    # PAUSE: Status auf research_complete → User muss bestätigen
                    await db.execute(
                        update(Simulation).where(Simulation.id == simulation_id)
                        .values(status=SimulationStatus.research_complete, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                    )
                    await db.commit()
                    logger.info(f"[{simulation_id}] Recherche abgeschlossen — warte auf User-Bestätigung")
                    return  # <-- STOP hier. User muss POST /research/approve aufrufen.

                # MarketContext existiert bereits (z.B. nach Approve)
                if existing_ctx:
                    market_context_summary = existing_ctx.prompt_summary
                    logger.info(f"[{simulation_id}] MarketContext geladen ({len(market_context_summary or '')} Zeichen)")

            # 1. Personas generieren falls noch nicht vorhanden
            result = await db.execute(
                select(Persona).where(Persona.simulation_id == simulation_id)
            )
            existing_personas = result.scalars().all()

            # Aktive Plattformen laden (vor Persona-Generierung für preferred_platform)
            active_platforms = await load_active_platforms(simulation_id, db)
            platform_names = get_platform_names(active_platforms)
            logger.info(f"[{simulation_id}] Aktive Plattformen: {platform_names}")

            if not existing_personas:
                persona_count = sim.config.get("persona_count", 10) if sim.config else 10

                # v1.1: distribution_template support
                distribution_template = getattr(sim, 'distribution_template', None)

                # Build kwargs — only pass distribution_template if the function accepts it
                gen_kwargs = dict(
                    product_description=sim.product_description,
                    target_market=sim.target_market or "",
                    industry=sim.industry or "",
                    persona_count=persona_count,
                    sim=sim,
                    db=db,
                    market_context_summary=market_context_summary,
                )
                if distribution_template is not None:
                    gen_kwargs["distribution_template"] = distribution_template
                gen_kwargs["platform_names"] = platform_names

                raw_personas = await generate_personas(**gen_kwargs)
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
                        # Legacy Entity-Typen
                        "persona_type", "entity_subtype",
                        # v1.1 Actor System
                        "actor_type", "subtype", "context", "traegerschaft",
                        "stance", "activation_latency", "function_tags",
                        "engagement_decay_rate",
                        # Realism Overhaul
                        "discussion_role", "rogers_category", "formality_level",
                        "response_length_tendency", "noise_propensity", "acquiescence_bias",
                        "survey_fatigue_rate", "regional_dialect", "b2b_b2c_mode",
                    }
                    clean = {k: v for k, v in p_data.items() if k in allowed}

                    # Realism Overhaul: verbal_tics + internal_contradictions → extra JSON
                    extra_realism = {}
                    if "verbal_tics" in p_data:
                        extra_realism["verbal_tics"] = p_data["verbal_tics"]
                    if "internal_contradictions" in p_data:
                        extra_realism["internal_contradictions"] = p_data["internal_contradictions"]

                    # v1.1: Store type-specific profile data
                    skip_fields = allowed | {"preferred_platform", "verbal_tics", "internal_contradictions"}
                    profile_fields = {k: v for k, v in p_data.items() if k not in skip_fields}
                    if profile_fields:
                        clean["profile_data"] = profile_fields

                    # v1.1: Backwards compatibility - map old persona_type to actor_type
                    if "actor_type" not in clean and "persona_type" in clean:
                        old_type = clean.get("persona_type", "individual")
                        type_mapping = {
                            "individual": "private_person",
                            "organization": "company",
                            "institution": "collective",
                            "politician": "private_person",
                        }
                        clean["actor_type"] = type_mapping.get(old_type, "private_person")

                    # v1.1: Set default activation_latency if not provided
                    if "activation_latency" not in clean:
                        try:
                            from app.simulation.tick_engine import ACTOR_BEHAVIOR
                            actor_type = clean.get("actor_type", "private_person")
                            behavior = ACTOR_BEHAVIOR.get(actor_type, ACTOR_BEHAVIOR["private_person"])
                            import random
                            clean["activation_latency"] = random.randint(behavior["latency_min"], behavior["latency_max"])
                        except (ImportError, KeyError):
                            clean["activation_latency"] = 0

                    # Initiale Plattform-Affinität aus aktiven Plattformen + preferred_platform
                    preferred = p_data.get("preferred_platform", platform_names[0] if platform_names else "feedbook")
                    # Wenn preferred_platform nicht in aktiven Plattformen, erste aktive wählen
                    if preferred not in platform_names and platform_names:
                        preferred = platform_names[0]
                    initial_affinity = build_platform_affinity(active_platforms, preferred)

                    # v1.1: Actor-Type-basierte Adjustierung
                    actor_type = clean.get("actor_type", "private_person")
                    if actor_type in ("authority", "collective", "validator", "research_institute"):
                        # Formelle Akteure bevorzugen formellere Plattformen
                        for pname in platform_names:
                            plat = next((p for p in active_platforms if p["name"] == pname), None)
                            if plat and plat.get("character") in ("institutionell", "fachlich"):
                                initial_affinity[pname] = initial_affinity.get(pname, 0.3) * 1.5
                    elif actor_type in ("influencer", "media"):
                        # Reichweiten-Akteure bevorzugen Boulevard/Öffentliche Plattformen
                        for pname in platform_names:
                            plat = next((p for p in active_platforms if p["name"] == pname), None)
                            if plat and plat.get("character") in ("boulevard", "oeffentlich"):
                                initial_affinity[pname] = initial_affinity.get(pname, 0.3) * 1.5

                    # Normalisieren
                    total_aff = sum(initial_affinity.values())
                    if total_aff > 0:
                        initial_affinity = {k: round(v / total_aff, 3) for k, v in initial_affinity.items()}

                    # Modul 2: Initiale Opinion-Dimensions
                    from app.simulation.tick_engine import _init_opinion_dimensions
                    initial_dims = _init_opinion_dimensions(clean.get("is_skeptic", False))

                    # Realism Overhaul: Discussion-Role nachrüsten falls nicht vorhanden
                    if not clean.get("discussion_role"):
                        from app.simulation.discussion_roles import assign_discussion_role
                        clean["discussion_role"] = assign_discussion_role(p_data)

                    # Realism Overhaul: Rogers-Category validieren
                    valid_rogers = {"innovator", "early_adopter", "early_majority", "late_majority", "laggard"}
                    if clean.get("rogers_category") not in valid_rogers:
                        from app.simulation.persona_generator import _classify_adopter_type
                        clean["rogers_category"] = _classify_adopter_type(p_data)

                    # Extra-Daten zusammenführen
                    extra_data = {"preferred_platform": preferred}
                    extra_data.update(extra_realism)

                    persona = Persona(
                        simulation_id=simulation_id,
                        current_state={
                            "platform_affinity": initial_affinity,
                            "opinion_dimensions": initial_dims,
                        },
                        extra=extra_data,
                        **clean,
                    )
                    db.add(persona)

                await db.flush()
                await _assign_social_connections(db, simulation_id)
                await db.commit()

            # Guard: Abort if no personas exist (e.g. generator failed)
            persona_count_result = await db.execute(
                select(func.count(Persona.id)).where(Persona.simulation_id == simulation_id)
            )
            if persona_count_result.scalar() == 0:
                logger.error(f"[{simulation_id}] Keine Personas vorhanden — Simulation abgebrochen")
                await db.execute(
                    update(Simulation).where(Simulation.id == simulation_id)
                    .values(status=SimulationStatus.failed, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                )
                await db.commit()
                return

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
                    market_context_summary=market_context_summary,
                    active_platforms=active_platforms,
                )

                # v1.1: Crowd Layer
                try:
                    from app.models.content import Post as PostModel
                    from sqlalchemy.orm import selectinload
                    posts_for_crowd = await db.execute(
                        select(PostModel)
                        .options(selectinload(PostModel.reactions))
                        .where(PostModel.simulation_id == simulation_id)
                        .where(PostModel.ingame_day == tick_num)
                    )
                    crowd_posts = posts_for_crowd.scalars().all()

                    personas_result = await db.execute(
                        select(Persona).where(Persona.simulation_id == simulation_id)
                    )
                    all_personas = personas_result.scalars().all()

                    await _process_crowd_layer(simulation_id, tick_num, db, all_personas, crowd_posts)
                except Exception as e:
                    logger.warning(f"[{simulation_id}] Crowd-Layer-Processing fehlgeschlagen: {e}")

                await db.execute(
                    update(Simulation)
                    .where(Simulation.id == simulation_id)
                    .values(current_tick=tick_num, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                )
                await db.commit()
                logger.info(f"[{simulation_id}] Tick {tick_num} abgeschlossen")

            # 3. Report automatisch generieren
            logger.info(f"[{simulation_id}] Starte automatische Report-Generierung")
            try:
                report_resolved = await resolve_for_phase(sim, "analysis_reports", db)
                await generate_report(simulation_id, db, resolved=report_resolved)
                logger.info(f"[{simulation_id}] Report generiert")
            except Exception as e:
                logger.warning(f"[{simulation_id}] Auto-Report fehlgeschlagen (Simulation trotzdem completed): {e}")

            # 4. Abschluss
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


async def create_multi_run_simulations(
    source_simulation_id: UUID,
    run_count: int = 3,
) -> tuple[UUID, list[UUID]]:
    """Erstellt N Kopien einer Simulation für Multi-Run-Vergleich.

    Gibt (run_group_id, [simulation_ids]) zurück.
    Die Simulationen werden erstellt aber NICHT gestartet — der Router startet sie.
    """
    run_group_id = _uuid.uuid4()
    simulation_ids: list[UUID] = []

    async with AsyncSessionLocal() as db:
        original = await db.get(Simulation, source_simulation_id)
        if not original:
            raise ValueError(f"Simulation {source_simulation_id} nicht gefunden")

        for i in range(run_count):
            clone = Simulation(
                name=f"{original.name} (Run {i + 1}/{run_count})",
                product_description=original.product_description,
                target_market=original.target_market,
                industry=original.industry,
                total_ticks=original.total_ticks,
                config=original.config,
                webhook_url=original.webhook_url,
                llm_provider=getattr(original, "llm_provider", "anthropic"),
                llm_model_fast=getattr(original, "llm_model_fast", None),
                llm_model_smart=getattr(original, "llm_model_smart", None),
                provider_config=getattr(original, "provider_config", None),
                status=SimulationStatus.pending,
                current_tick=0,
                run_group_id=run_group_id,
                run_index=i,
                # v1.1 fields
                research_snapshot_id=getattr(original, "research_snapshot_id", None),
                stagnation_mode=getattr(original, "stagnation_mode", "mild"),
                distribution_template=getattr(original, "distribution_template", None),
            )
            db.add(clone)
            await db.flush()
            simulation_ids.append(clone.id)

        await db.commit()

    return run_group_id, simulation_ids


async def run_multi_simulation_background(
    run_group_id: UUID,
    simulation_ids: list[UUID],
):
    """Startet alle Simulationen einer Multi-Run-Gruppe sequentiell.

    Sequentiell statt parallel, um API-Rate-Limits nicht zu überschreiten.
    """
    for sim_id in simulation_ids:
        # Status auf running setzen
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Simulation)
                .where(Simulation.id == sim_id)
                .values(
                    status=SimulationStatus.running,
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            await db.commit()

        try:
            await run_simulation_background(sim_id)
        except Exception as e:
            logger.error(f"[Multi-Run {run_group_id}] Run {sim_id} fehlgeschlagen: {e}")
            # Weitermachen mit nächstem Run

    logger.info(f"[Multi-Run {run_group_id}] Alle {len(simulation_ids)} Runs abgeschlossen")
