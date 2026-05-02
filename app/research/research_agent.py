"""
Research Agent: Orchestriert die komplette Web-Recherche.
Generiert Queries → führt Web-Suche durch → synthetisiert Context Document.
"""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import get_provider
from app.llm.resolver import ResolvedProvider, resolve_for_phase
from app.models import Simulation, MarketContext
from app.research.web_search import search_web, SearchSession
from app.research.context_builder import generate_search_queries, synthesize_context

logger = logging.getLogger("simulator.research")


async def run_market_research(
    simulation_id: UUID,
    db: AsyncSession,
    resolved: ResolvedProvider | None = None,
) -> MarketContext:
    """Führt die komplette Marktrecherche durch und speichert das Ergebnis.

    1. Generiert Suchqueries basierend auf Simulation-Parametern
    2. Führt Web-Suchen durch
    3. Synthetisiert Ergebnisse zu MarketContext
    4. Speichert in DB

    Bei Fehler in der Web-Suche: Fallback auf reines LLM-Wissen (kein Abbruch).
    """
    sim = await db.get(Simulation, simulation_id)
    if not sim:
        raise ValueError(f"Simulation {simulation_id} nicht gefunden")

    # Provider resolven
    if resolved:
        provider = resolved.provider
        model = resolved.model
    else:
        provider = get_provider(getattr(sim, "llm_provider", None))
        model = getattr(sim, "llm_model_smart", None)

    logger.info(f"[{simulation_id}] Starte Marktrecherche (provider={provider.name})")

    # --- 1. Suchqueries generieren ---
    try:
        query_data = await generate_search_queries(
            product_description=sim.product_description,
            target_market=sim.target_market or "",
            industry=sim.industry or "",
            provider=provider,
            model=model,
        )
    except Exception as e:
        logger.error(f"[{simulation_id}] Query-Generierung fehlgeschlagen: {e}")
        query_data = {
            "macro_queries": [f"Wirtschaftslage {sim.target_market or 'Deutschland'} 2026"],
            "industry_queries": [f"{sim.industry or 'Technologie'} Markt Trends 2026"],
            "target_group_queries": [f"{sim.industry or 'Technologie'} Zielgruppe Herausforderungen"],
        }

    all_queries = (
        query_data.get("macro_queries", [])
        + query_data.get("industry_queries", [])
        + query_data.get("target_group_queries", [])
    )

    logger.info(f"[{simulation_id}] {len(all_queries)} Suchqueries generiert")

    # --- 2. Web-Suche durchführen ---
    search_session: SearchSession
    try:
        search_session = await search_web(all_queries)
        logger.info(
            f"[{simulation_id}] Web-Suche: {len(search_session.results)} Ergebnisse, "
            f"{len(search_session.errors)} Fehler"
        )
    except Exception as e:
        logger.warning(f"[{simulation_id}] Web-Suche komplett fehlgeschlagen: {e} — Fallback auf LLM-Wissen")
        search_session = SearchSession()

    # --- 3. Context synthetisieren ---
    try:
        context_data = await synthesize_context(
            product_description=sim.product_description,
            target_market=sim.target_market or "",
            industry=sim.industry or "",
            search_session=search_session,
            provider=provider,
            model=model,
        )
    except Exception as e:
        logger.error(f"[{simulation_id}] Context-Synthese fehlgeschlagen: {e}")
        # Minimaler Fallback-Context
        context_data = {
            "macro_context": f"Keine Recherche-Daten verfügbar. Zielmarkt: {sim.target_market or 'DACH'}.",
            "industry_context": f"Branche: {sim.industry or 'Nicht spezifiziert'}. Keine aktuellen Daten.",
            "target_group_context": "Keine zielgruppenspezifischen Daten verfügbar.",
            "prompt_summary": (
                f"Zielmarkt: {sim.target_market or 'DACH'}. "
                f"Branche: {sim.industry or 'Technologie'}. "
                "Aktuelle Marktdaten konnten nicht recherchiert werden — "
                "verwende allgemeines Branchenwissen."
            ),
        }

    # --- 4. In DB speichern ---
    raw_sources = [
        {
            "query": r.query,
            "title": r.title,
            "snippet": r.snippet,
            "url": r.url,
        }
        for r in search_session.results
    ]

    market_context = MarketContext(
        simulation_id=simulation_id,
        macro_context=context_data.get("macro_context", ""),
        industry_context=context_data.get("industry_context", ""),
        target_group_context=context_data.get("target_group_context", ""),
        prompt_summary=context_data.get("prompt_summary", ""),
        raw_sources=raw_sources,
        research_queries=all_queries,
        research_mode="deep",
    )
    db.add(market_context)
    await db.flush()

    logger.info(
        f"[{simulation_id}] Marktrecherche abgeschlossen: "
        f"{len(raw_sources)} Quellen, Context gespeichert"
    )

    return market_context
