"""
Stress-Test-Mechaniken für die Simulation.

Drei Modi:
1. Contrarian-Injection: Generiert starke Gegen-Narrative an bestimmten Tagen
2. Sensitivity-Test: Variiert den Skeptiker-Anteil und vergleicht Ergebnisse
3. Remove-and-Rerun: Entfernt einflussreichste Akteure und prüft Stabilität
"""
import logging
import uuid as _uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import (
    Simulation, SimulationStatus, Persona, Post, Platform,
    InfluenceEvent,
)

logger = logging.getLogger("agora.stress_test")


async def inject_contrarian_posts(
    simulation_id: UUID,
    db: AsyncSession,
    ingame_day: int,
    count: int = 3,
) -> list[dict]:
    """Injiziert Gegen-Narrative als System-Posts.

    Erstellt Posts von fiktiven "externen Experten" die den aktuellen
    Konsens direkt herausfordern. Verwendet die aktuellen Dimensions-Durchschnitte
    um gezielte Gegenargumente zu formulieren.
    """
    # Aktuelle Dimensions-Durchschnitte laden
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.personas))
        .where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one()

    # Stärkste Dimension finden (die am meisten Konsens hat)
    dims_avg: dict[str, float] = {}
    for p in sim.personas:
        state = p.current_state or {}
        opinion_dims = state.get("opinion_dimensions", {})
        for key, val in opinion_dims.items():
            dims_avg.setdefault(key, []).append(val)

    strongest_dims = []
    for key, vals in dims_avg.items():
        if vals:
            avg = sum(vals) / len(vals)
            strongest_dims.append((key, avg))
    strongest_dims.sort(key=lambda x: abs(x[1]), reverse=True)

    # Gegen-Narrative für die Top-Dimensionen generieren
    contrarian_templates = {
        "product_quality": {
            "positive_counter": "Unabhängige Tests zeigen erhebliche Qualitätsmängel. Wir haben ähnliche Tools evaluiert und die Fehlerrate war inakzeptabel für den Enterprise-Einsatz.",
            "negative_counter": "Die Qualitätsbedenken sind übertrieben. Vergleichbare Tools haben in Pilotprojekten solide Ergebnisse geliefert — die Kritik basiert auf veralteten Annahmen.",
        },
        "price_fairness": {
            "positive_counter": "Der Markt bietet günstigere Alternativen mit vergleichbarer Leistung. Das aktuelle Pricing rechtfertigt den Mehrwert nicht.",
            "negative_counter": "Die Kosten relativieren sich bei genauerer Betrachtung. Wer den TCO rechnet statt nur den Lizenzpreis, kommt zu anderen Ergebnissen.",
        },
        "brand_trust": {
            "positive_counter": "Vertrauen muss verdient werden. Bisher fehlen belastbare Referenzen und unabhängige Validierungen.",
            "negative_counter": "Das Misstrauen ist unbegründet. Die Referenzen existieren — man muss nur mit den richtigen Leuten sprechen.",
        },
        "innovation": {
            "positive_counter": "Was hier als Innovation verkauft wird, ist in anderen Märkten längst Standard. Der europäische Markt hat den Anschluss verpasst.",
            "negative_counter": "Nicht jede Neuerung ist ein Fortschritt. Bewährte Methoden haben ihren Wert, und die sogenannte Innovation löst Probleme, die niemand hat.",
        },
        "social_proof": {
            "positive_counter": "Die Begeisterung erinnert an klassische Hype-Zyklen. Wir haben das schon bei Blockchain und NFTs gesehen — Konsens ist kein Qualitätsmerkmal.",
            "negative_counter": "Wenn so viele erfahrene Fachleute unabhängig zu ähnlichen Einschätzungen kommen, sollte man das nicht als Hype abtun.",
        },
        "ethical_concerns": {
            "positive_counter": "Die ethischen Implikationen werden systematisch heruntergespielt. Datenschutz-Audits ersetzen keine fundamentale Auseinandersetzung mit KI-Bias.",
            "negative_counter": "Ethik-Bedenken dürfen nicht zum Innovationsstopper werden. Die relevanten Frameworks existieren und werden angewendet.",
        },
        "personal_relevance": {
            "positive_counter": "Nicht jede Branche profitiert gleichermaßen. Die generalisierten Erfolgsversprechen ignorieren branchenspezifische Besonderheiten.",
            "negative_counter": "Wer die Relevanz für das eigene Geschäft nicht erkennt, hat den Anwendungsfall nicht verstanden — nicht das Tool.",
        },
    }

    injected = []
    for i, (dim_key, avg_val) in enumerate(strongest_dims[:count]):
        templates = contrarian_templates.get(dim_key, {})
        if avg_val > 0:
            content = templates.get("positive_counter", f"Die positive Einschätzung zu {dim_key} ist nicht belastbar.")
        else:
            content = templates.get("negative_counter", f"Die negative Einschätzung zu {dim_key} sollte hinterfragt werden.")

        # Als Post von "externem Experten" einfügen — nutze eine zufällige Persona als Autor
        # (damit FK-Constraints erfüllt sind)
        contrarian_persona = sim.personas[i % len(sim.personas)]

        post = Post(
            simulation_id=simulation_id,
            author_id=contrarian_persona.id,
            platform=Platform.threadit if i % 2 == 0 else Platform.feedbook,
            content=f"[Externe Perspektive] {content}",
            ingame_day=ingame_day,
            subreddit="r/Marktforschung" if i % 2 == 0 else None,
        )
        db.add(post)
        injected.append({
            "dimension": dim_key,
            "current_avg": round(avg_val, 3),
            "direction": "counter_positive" if avg_val > 0 else "counter_negative",
            "content": content[:100],
        })

    await db.flush()
    return injected


async def create_sensitivity_test(
    source_simulation_id: UUID,
    skeptic_rate: float = 0.6,
) -> UUID:
    """Erstellt eine Kopie der Simulation mit verändertem Skeptiker-Anteil.

    Gibt die ID der neuen Simulation zurück.
    """
    async with AsyncSessionLocal() as db:
        original = await db.get(Simulation, source_simulation_id)
        if not original:
            raise ValueError(f"Simulation {source_simulation_id} nicht gefunden")

        config = dict(original.config or {})
        config["skeptic_override_rate"] = skeptic_rate

        clone = Simulation(
            name=f"{original.name} (Sensitivity: {int(skeptic_rate * 100)}% Skeptiker)",
            product_description=original.product_description,
            target_market=original.target_market,
            industry=original.industry,
            total_ticks=original.total_ticks,
            config=config,
            webhook_url=original.webhook_url,
            llm_provider=getattr(original, "llm_provider", "anthropic"),
            llm_model_fast=getattr(original, "llm_model_fast", None),
            llm_model_smart=getattr(original, "llm_model_smart", None),
            provider_config=getattr(original, "provider_config", None),
            status=SimulationStatus.pending,
            current_tick=0,
        )
        db.add(clone)
        await db.flush()
        clone_id = clone.id
        await db.commit()

    return clone_id


async def find_top_influencers(
    simulation_id: UUID,
    db: AsyncSession,
    top_n: int = 3,
) -> list[dict]:
    """Findet die einflussreichsten Personas einer Simulation.

    Basiert auf Anzahl ausgehender Influence-Events.
    """
    result = await db.execute(
        select(
            InfluenceEvent.source_persona_id,
            func.count(InfluenceEvent.id).label("influence_count"),
        )
        .where(InfluenceEvent.simulation_id == simulation_id)
        .group_by(InfluenceEvent.source_persona_id)
        .order_by(func.count(InfluenceEvent.id).desc())
        .limit(top_n)
    )
    rows = result.all()

    influencers = []
    for row in rows:
        persona = await db.get(Persona, row.source_persona_id)
        influencers.append({
            "persona_id": str(row.source_persona_id),
            "name": persona.name if persona else "Unbekannt",
            "influence_count": row.influence_count,
        })

    return influencers


async def create_remove_and_rerun(
    source_simulation_id: UUID,
    remove_persona_ids: list[UUID],
) -> UUID:
    """Erstellt eine Kopie der Simulation ohne bestimmte Personas.

    Die entfernten Personas werden in der Config vermerkt, damit der
    Persona-Generator sie bei der Neugenerierung überspringt.
    """
    async with AsyncSessionLocal() as db:
        original = await db.get(Simulation, source_simulation_id)
        if not original:
            raise ValueError(f"Simulation {source_simulation_id} nicht gefunden")

        # Persona-Namen der zu entfernenden Personas laden
        remove_names = []
        for pid in remove_persona_ids:
            persona = await db.get(Persona, pid)
            if persona:
                remove_names.append(persona.name)

        config = dict(original.config or {})
        config["exclude_persona_names"] = remove_names

        clone = Simulation(
            name=f"{original.name} (ohne {', '.join(remove_names[:3])})",
            product_description=original.product_description,
            target_market=original.target_market,
            industry=original.industry,
            total_ticks=original.total_ticks,
            config=config,
            webhook_url=original.webhook_url,
            llm_provider=getattr(original, "llm_provider", "anthropic"),
            llm_model_fast=getattr(original, "llm_model_fast", None),
            llm_model_smart=getattr(original, "llm_model_smart", None),
            provider_config=getattr(original, "provider_config", None),
            status=SimulationStatus.pending,
            current_tick=0,
        )
        db.add(clone)
        await db.flush()
        clone_id = clone.id
        await db.commit()

    return clone_id
