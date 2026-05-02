"""
Analyse-Layer: Generiert den finalen Report via Claude Sonnet (async) mit Tool Use.
"""
import json
import logging
from uuid import UUID

logger = logging.getLogger("agora.analysis")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.llm import get_provider
from app.llm.resolver import ResolvedProvider
from app.models import AnalysisReport, Post, Comment, Simulation, InfluenceEvent, MarketContext

def _build_analyst_system_prompt(
    sim,
    persona_type_counts: dict[str, int],
    total_posts: int,
    total_events: int,
) -> str:
    """Baut einen szenarienspezifischen System-Prompt für die Analyse."""
    # Szenario-Kontext ableiten
    orgs = persona_type_counts.get("organization", 0)
    insts = persona_type_counts.get("institution", 0)
    pols = persona_type_counts.get("politician", 0)
    individuals = persona_type_counts.get("individual", 0)
    total = sum(persona_type_counts.values()) or 1
    org_ratio = (orgs + insts + pols) / total

    if org_ratio > 0.4:
        scenario_hint = (
            "Dies ist ein B2B/institutionelles Szenario mit vielen Organisationen und Institutionen. "
            "Analysiere besonders: Entscheidungsprozesse in Organisationen, regulatorische Hürden, "
            "Beschaffungszyklen, Fachdiskurse zwischen Institutionen, und ob Branchenverbände/Prüfstellen "
            "als Multiplikatoren oder Blocker auftreten. Vergleiche die Perspektiven von Fachleuten, "
            "Organisationen und Regulierern."
        )
    elif org_ratio > 0.15:
        scenario_hint = (
            "Dies ist ein gemischtes Szenario mit Einzelpersonen und relevanten Organisationen. "
            "Analysiere sowohl die öffentliche Meinung der Einzelpersonen als auch die strategischen "
            "Positionierungen der Unternehmen und Institutionen. Wo divergieren Experten-Meinung und "
            "Konsumenten-Stimmung?"
        )
    else:
        scenario_hint = (
            "Dies ist ein konsumentenorientiertes B2C-Szenario. "
            "Analysiere besonders: Konsumenten-Sentiment, virale Dynamiken, Mundpropaganda, "
            "Kaufbereitschaft, und ob Skeptiker andere Konsumenten beeinflusst haben."
        )

    actor_breakdown = ", ".join(
        f"{count} {typ}" for typ, count in sorted(persona_type_counts.items(), key=lambda x: -x[1])
    )

    return f"""Du bist ein Senior-Analyst einer renommierten Strategieberatung.
Du erstellst professionelle Marktanalyse-Reports auf Basis simulierter Gesellschaftsdaten.

WICHTIG: Dies ist eine SIMULATION, keine echte Marktforschung. Deine Analyse muss das transparent reflektieren.

{scenario_hint}

Akteur-Mix dieser Simulation: {actor_breakdown}.
Datenbasis: {total_posts} Beiträge, {total_events} Einfluss-Ereignisse.

## Konfidenz-Bewertung
Bewerte JEDE Kernaussage mit einem Konfidenz-Level:
- **[HOHE KONFIDENZ]**: Ergebnis ist über mehrere Akteure konsistent, überlebt verschiedene Perspektiven
- **[MITTLERE KONFIDENZ]**: Ergebnis plausibel, aber abhängig von wenigen Schlüsselakteuren oder Annahmen
- **[NIEDRIGE KONFIDENZ]**: Ergebnis möglicherweise Artefakt der Simulation (Echokammer, LLM-Bias, kleine Stichprobe)

Achte besonders auf:
- Quantitative Claims von Personas (z.B. "+23% CTR") — das sind KEINE echten Daten, sondern Persona-Behauptungen
- Konsens-Bildung, die zu schnell geht (Echokammer-Risiko)
- Überzeugungsketten, die auf einzelnen Akteuren basieren (fragil)

## Formatierung
- Schreibe in professionellem, sachlichem Deutsch
- Verwende Markdown: **Fettdruck** für Kernaussagen, Aufzählungen für Empfehlungen
- Quantifiziere wo möglich ("73% der Labore zeigten Interesse" statt "viele waren interessiert")
- Zitiere konkrete Beispiele aus der Simulation (Name, Post-Inhalt, Kontext)
- Jede Sektion soll eigenständig lesbar sein — kein "wie oben erwähnt"
- Verwende Zwischenüberschriften (### ) innerhalb langer Sektionen"""

ANALYSIS_REPORT_TOOL_NAME = "analysis_report"
ANALYSIS_REPORT_TOOL_DESC = "Strukturierter Analyse-Report der Simulation"
ANALYSIS_REPORT_TOOL_SCHEMA = {
        "type": "object",
        "properties": {
            "full_report": {
                "type": "string",
                "description": (
                    "Executive Summary als Markdown (800-1500 Wörter). "
                    "Struktur: ### Ausgangslage, ### Kernerkenntnisse (3-5 nummerierte Punkte mit **Fett** für Kernaussagen), "
                    "### Risiken & Chancen, ### Strategische Empfehlungen (als Aufzählung). "
                    "Quantifiziere: Prozentsätze, Persona-Anzahlen, Vergleichswerte."
                ),
            },
            "sentiment_over_time": {
                "type": "string",
                "description": (
                    "Markdown: Sentiment-Verlauf über die simulierten Tage. "
                    "Beschreibe Phase für Phase: Anfangsphase (Tag 1-3), Mittelteil, Endphase. "
                    "Nenne konkrete Stimmungsumschwünge mit Ursache und betroffenen Akteuren."
                ),
            },
            "key_turning_points": {
                "type": "string",
                "description": (
                    "Markdown: 3-6 Wendepunkte als nummerierte Liste. "
                    "Pro Punkt: **Tag X — Titel**: Was passiert ist, wer beteiligt war, welche Auswirkung. "
                    "Zitiere konkrete Posts oder Akteur-Namen."
                ),
            },
            "criticism_points": {
                "type": "string",
                "description": (
                    "Markdown: Hauptkritikpunkte als Aufzählung. "
                    "Pro Punkt: **Kritikthema**: Wer kritisiert (mit Namen/Typ), Kernargument, "
                    "wie viele Akteure teilen diese Kritik (%). Sortiert nach Schwere."
                ),
            },
            "opportunities": {
                "type": "string",
                "description": (
                    "Markdown: Erkannte Chancen und positive Signale. "
                    "Pro Punkt: **Chance**: Beschreibung, welche Akteure positiv reagiert haben, "
                    "geschätztes Potenzial. Konkrete Zitate aus der Simulation einbauen."
                ),
            },
            "target_segment_analysis": {
                "type": "string",
                "description": (
                    "Markdown: Zielgruppen-Segmentierung mit ### pro Segment. "
                    "Pro Segment: Beschreibung, Größe (Anzahl/%), Haltung, Schlüssel-Akteure namentlich, "
                    "Empfehlung für Ansprache. Bei B2B: nach Organisationstyp segmentieren."
                ),
            },
            "unexpected_findings": {
                "type": "string",
                "description": (
                    "Markdown: 3-5 überraschende Erkenntnisse. "
                    "Dinge die man nicht erwartet hätte. Konkret und mit Evidenz aus der Simulation."
                ),
            },
            "influence_network": {
                "type": "string",
                "description": (
                    "Markdown: Analyse des Einfluss-Netzwerks. "
                    "### Top-Influencer (wer hat die meisten Meinungen verändert, mit Zahlen), "
                    "### Überzeugungsketten (Pfade: A beeinflusst B beeinflusst C), "
                    "### Einflussreichste Beiträge (konkrete Post-Inhalte zitieren)."
                ),
            },
            "platform_dynamics": {
                "type": "string",
                "description": (
                    "Markdown: FeedBook vs. Threadit Vergleich. "
                    "Tonalität-Unterschiede, welche Akteure wo aktiver sind, "
                    "ob bestimmte Themen plattformspezifisch diskutiert werden."
                ),
            },
            "network_evolution": {
                "type": "string",
                "description": (
                    "Markdown: Netzwerk-Dynamik über die Simulation. "
                    "Community-Bildung, Echokammern, ob sich Lager gebildet haben, "
                    "Brücken-Akteure zwischen Communities."
                ),
            },
            "confidence_assessment": {
                "type": "string",
                "description": (
                    "Markdown: Konfidenz-Bewertung der Ergebnisse. "
                    "### Hohe Konfidenz: Aussagen die über mehrere Akteure und Perspektiven konsistent sind. "
                    "### Mittlere Konfidenz: Plausible aber nicht robuste Aussagen. "
                    "### Niedrige Konfidenz: Möglicherweise Artefakte (Echokammer, zu schnelle Konvergenz, Einzelperson-Abhängigkeit). "
                    "Für jede Kategorie: konkrete Aussagen aus dem Report zuordnen mit Begründung."
                ),
            },
            "methodology_limitations": {
                "type": "string",
                "description": (
                    "Markdown: Was diese Simulation NICHT leisten kann. "
                    "Ehrliche Einschätzung der Grenzen: "
                    "- Persona-Verhalten basiert auf LLM-Generierung, nicht auf echten Menschen "
                    "- Quantitative Claims von Personas sind KEINE echten Marktdaten "
                    "- Echokammer-Effekte können Konsens-Ergebnisse verzerren "
                    "- Die Simulation testet Narrative, nicht Kaufverhalten "
                    "- Konkrete Empfehlung, welche Erkenntnisse vor einer Entscheidung real validiert werden sollten"
                ),
            },
        },
        "required": [
            "full_report",
            "sentiment_over_time",
            "key_turning_points",
            "criticism_points",
            "opportunities",
            "target_segment_analysis",
            "unexpected_findings",
            "influence_network",
            "platform_dynamics",
            "network_evolution",
            "confidence_assessment",
            "methodology_limitations",
        ],
}


async def generate_report(
    simulation_id: UUID,
    db: AsyncSession,
    provider_name: str | None = None,
    model: str | None = None,
    resolved: ResolvedProvider | None = None,
) -> AnalysisReport:
    """Generiert den Analyse-Report asynchron via konfigurierten LLM-Provider.

    Lädt alle Posts via selectinload (kein Lazy Loading).
    Speichert AnalysisReport in DB und committet.

    resolved: Neues System — überschreibt provider_name/model wenn gesetzt.
    """
    if resolved:
        provider = resolved.provider
        model = resolved.model
        temperature = resolved.temperature
        top_p = resolved.top_p
        top_k = resolved.top_k
    else:
        provider = get_provider(provider_name)
        temperature = None
        top_p = None
        top_k = None
    # Simulation laden
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.personas))
        .where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one()

    # Posts mit allen Relationships laden
    posts_result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.author),
            selectinload(Post.comments).selectinload(Comment.author),
            selectinload(Post.reactions),
        )
        .where(Post.simulation_id == simulation_id)
        .order_by(Post.ingame_day)
    )
    posts = posts_result.scalars().all()

    # Influence-Events laden
    influence_result = await db.execute(
        select(InfluenceEvent)
        .where(InfluenceEvent.simulation_id == simulation_id)
        .order_by(InfluenceEvent.ingame_day)
    )
    influence_events = influence_result.scalars().all()

    # Post-Daten für den Prompt aufbereiten — gekürzt um Context-Limit einzuhalten
    # Bei großen Simulationen: Content auf 200 Zeichen kürzen, max 300 Posts
    MAX_POSTS = 300
    MAX_CONTENT_LEN = 200
    post_data = []
    for post in posts[:MAX_POSTS]:
        content = post.content
        if len(content) > MAX_CONTENT_LEN:
            content = content[:MAX_CONTENT_LEN] + "…"
        comments = []
        for c in post.comments[:3]:  # Max 3 Kommentare pro Post
            c_content = c.content
            if len(c_content) > MAX_CONTENT_LEN:
                c_content = c_content[:MAX_CONTENT_LEN] + "…"
            comments.append({
                "author": c.author.name if c.author else "?",
                "content": c_content,
            })
        post_data.append(
            {
                "author": post.author.name if post.author else "Unbekannt",
                "is_skeptic": post.author.is_skeptic if post.author else False,
                "platform": post.platform.value,
                "ingame_day": post.ingame_day,
                "content": content,
                "comments": comments,
                "reactions_count": len(post.reactions),
            }
        )
    if len(posts) > MAX_POSTS:
        logger.info(f"[{simulation_id}] Report: {len(posts)} Posts auf {MAX_POSTS} gekürzt")

    # Influence-Events zusammenfassen — max 200 Events, Beschreibung gekürzt
    MAX_EVENTS = 200
    persona_name_map = {str(p.id): p.name for p in sim.personas}
    influence_data = []
    for event in influence_events[:MAX_EVENTS]:
        desc = event.description or ""
        if len(desc) > 150:
            desc = desc[:150] + "…"
        influence_data.append({
            "day": event.ingame_day,
            "source": persona_name_map.get(str(event.source_persona_id), "Unbekannt"),
            "target": persona_name_map.get(str(event.target_persona_id), "Unbekannt"),
            "type": event.influence_type,
            "description": desc,
        })
    if len(influence_events) > MAX_EVENTS:
        logger.info(f"[{simulation_id}] Report: {len(influence_events)} Events auf {MAX_EVENTS} gekürzt")

    # Persona-Endzustände für den Report (mit Opinion-Dimensionen — Modul 2)
    persona_states = []
    for p in sim.personas:
        state = p.current_state or {}
        opinion_dims = state.get("opinion_dimensions", {})
        persona_entry = {
            "name": p.name,
            "is_skeptic": p.is_skeptic,
            "final_opinion": state.get("opinion_evolution", p.initial_opinion),
            "final_mood": state.get("mood", "neutral"),
            "platform_affinity": state.get("platform_affinity", {}),
            "connection_count": len(p.social_connections or []),
        }
        if opinion_dims:
            persona_entry["opinion_dimensions"] = opinion_dims
            # Durchschnittliche Gesamt-Meinung berechnen
            avg = sum(opinion_dims.values()) / len(opinion_dims)
            persona_entry["overall_opinion_score"] = round(avg, 2)
        persona_states.append(persona_entry)

    # Dimensionsanalyse über alle Personas (für den Prompt)
    all_dims: dict[str, list[float]] = {}
    for p in sim.personas:
        state = p.current_state or {}
        dims = state.get("opinion_dimensions", {})
        for key, val in dims.items():
            all_dims.setdefault(key, []).append(val)

    dimension_summary = {}
    for key, values in all_dims.items():
        if values:
            dimension_summary[key] = {
                "avg": round(sum(values) / len(values), 2),
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "positive_pct": round(sum(1 for v in values if v > 0.1) / len(values) * 100, 1),
            }

    skeptic_count = sum(1 for p in sim.personas if p.is_skeptic)

    # Persona-Typ-Statistiken für dynamischen System-Prompt
    persona_type_counts: dict[str, int] = {}
    for p in sim.personas:
        ptype = getattr(p, "persona_type", "individual") or "individual"
        persona_type_counts[ptype] = persona_type_counts.get(ptype, 0) + 1

    # Dynamischen System-Prompt bauen
    system_prompt = _build_analyst_system_prompt(
        sim, persona_type_counts, len(posts), len(influence_events),
    )

    simulation_context = f"""Produkt: {sim.product_description}
Zielmarkt: {sim.target_market}
Branche: {sim.industry}
Simulierte Tage: {sim.current_tick}
Akteure gesamt: {len(sim.personas)} ({', '.join(f'{v} {k}' for k, v in sorted(persona_type_counts.items(), key=lambda x: -x[1]))})
Skeptiker: {skeptic_count} ({round(skeptic_count / max(len(sim.personas), 1) * 100)}%)
Beiträge: {len(posts)} | Einfluss-Events: {len(influence_events)}"""

    influence_section = ""
    if influence_data:
        influence_section = f"""

Influence-Events (wer hat wen beeinflusst):
{json.dumps(influence_data, ensure_ascii=False, indent=2)}
"""

    persona_states_section = f"""

Persona-Endzustände:
{json.dumps(persona_states, ensure_ascii=False, indent=2)}
"""

    dimension_section = ""
    if dimension_summary:
        dimension_section = f"""

Meinungsdimensionen-Analyse (Durchschnitt über alle Personas):
{json.dumps(dimension_summary, ensure_ascii=False, indent=2)}

Interpretation: product_quality/price_fairness/brand_trust/innovation/ethical_concerns/social_proof/personal_relevance
Werte: -1.0 (sehr negativ) bis +1.0 (sehr positiv), positive_pct = % der Personas mit positivem Wert (>0.1)
"""

    # MarketContext laden (falls Deep Mode)
    market_context_section = ""
    ctx_result = await db.execute(
        select(MarketContext).where(MarketContext.simulation_id == simulation_id)
    )
    market_ctx = ctx_result.scalar_one_or_none()
    if market_ctx and market_ctx.prompt_summary:
        market_context_section = f"""

Marktkontext (aus Web-Recherche vor der Simulation):
{market_ctx.prompt_summary}

Berücksichtige diesen realen Marktkontext bei der Analyse — vergleiche ob die Simulationsergebnisse
zu den recherchierten Marktbedingungen passen oder davon abweichen.
"""

    prompt = f"""Analysiere diese Simulation:

{simulation_context}
{market_context_section}
Alle simulierten Beiträge (chronologisch):
{json.dumps(post_data, ensure_ascii=False, indent=2)}
{influence_section}
{persona_states_section}
{dimension_section}
Erstelle einen strukturierten Report mit:
1. Sentiment-Verlauf über die simulierten Tage
2. Wichtige Wendepunkte (was hat die Stimmung gekippt?)
3. Hauptkritikpunkte und -ängste
4. Erkannte Chancen und positive Reaktionen
5. Zielgruppen-Segmentierung (wer reagiert wie?)
6. Überraschende oder unerwartete Erkenntnisse
7. Empfehlungen für Produkt/Kampagne
8. Influence-Netzwerk: Wer hat wen überzeugt? Welche Posts waren besonders einflussreich?
9. Plattform-Analyse: Wo wurde positiver/negativer diskutiert? Plattform-Migration?
10. Netzwerk-Dynamik: Haben sich Communities gebildet? Echokammern?
11. Meinungsdimensionen: Welche Dimensionen (Preis, Qualität, Marke etc.) waren am stärksten/schwächsten? \
    Konkrete Aussagen wie "73% der Skeptiker wurden bei Produktqualität überzeugt, aber Preis bleibt Dealbreaker"
12. Konfidenz-Bewertung: Welche Erkenntnisse sind belastbar (hohe Konfidenz), welche fragil (niedrig)?
13. Methodische Grenzen: Was kann diese Simulation NICHT leisten? Was muss real validiert werden?

Sei konkret, zitiere Beispiele aus der Simulation.
Sei EHRLICH über die Grenzen der Methodik — Glaubwürdigkeit entsteht durch Transparenz, nicht durch Überversprechen."""

    logger.info(
        f"[{simulation_id}] Starte Report-Generierung ({len(posts)} Posts, provider={provider.name})"
    )
    data = await provider.call_tool(
        tier="smart",
        system=system_prompt,
        cache_system=True,
        user_blocks=[{"text": prompt}],
        tool_name=ANALYSIS_REPORT_TOOL_NAME,
        tool_description=ANALYSIS_REPORT_TOOL_DESC,
        tool_schema=ANALYSIS_REPORT_TOOL_SCHEMA,
        max_tokens=16000,
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )

    if "full_report" not in data:
        logger.warning(
            f"[{simulation_id}] Report möglicherweise abgeschnitten "
            f"(fields={list(data.keys())})"
        )

    placeholder = "— im Report nicht behandelt —"
    report = AnalysisReport(
        simulation_id=simulation_id,
        full_report=data.get("full_report", placeholder),
        sentiment_over_time=data.get("sentiment_over_time", placeholder),
        key_turning_points=data.get("key_turning_points", placeholder),
        criticism_points=data.get("criticism_points", placeholder),
        opportunities=data.get("opportunities", placeholder),
        target_segment_analysis=data.get("target_segment_analysis", placeholder),
        unexpected_findings=data.get("unexpected_findings", placeholder),
        influence_network=data.get("influence_network", placeholder),
        platform_dynamics=data.get("platform_dynamics", placeholder),
        network_evolution=data.get("network_evolution", placeholder),
        confidence_assessment=data.get("confidence_assessment", placeholder),
        methodology_limitations=data.get("methodology_limitations", placeholder),
    )
    db.add(report)
    await db.commit()
    logger.info(f"[{simulation_id}] Report fertig")
    await db.refresh(report)

    return report
