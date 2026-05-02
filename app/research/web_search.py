"""
Web-Search-Wrapper: Führt Web-Suchen via duckduckgo-search durch.
Kein API-Key nötig, handled Anti-Bot-Maßnahmen automatisch.
Fallback: Leere Ergebnisse (LLM nutzt dann eigenes Wissen).
"""
import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("agora.research.web_search")

MAX_QUERIES = 10
RESULTS_PER_QUERY = 5


@dataclass
class SearchResult:
    title: str
    snippet: str
    url: str
    query: str


@dataclass
class SearchSession:
    results: list[SearchResult] = field(default_factory=list)
    queries_executed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _search_sync(query: str, max_results: int = RESULTS_PER_QUERY) -> list[SearchResult]:
    """Synchrone DuckDuckGo-Suche (wird in Thread ausgeführt)."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, region="de-de", max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    snippet=r.get("body", "")[:300],
                    url=r.get("href", ""),
                    query=query,
                ))
        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo-Suche fehlgeschlagen fuer '{query}': {e}")
        return []


async def search_web(queries: list[str]) -> SearchSession:
    """Führt mehrere Web-Suchen durch und sammelt Ergebnisse.

    Nutzt duckduckgo-search (synchron, in Thread-Pool ausgeführt).
    Bei Fehler wird die Query übersprungen (kein Abbruch).
    """
    session = SearchSession()
    queries = queries[:MAX_QUERIES]

    loop = asyncio.get_event_loop()

    for query in queries:
        try:
            results = await loop.run_in_executor(None, _search_sync, query)
            session.results.extend(results)
            session.queries_executed.append(query)
            logger.debug(f"Suche '{query}': {len(results)} Ergebnisse")
        except Exception as e:
            logger.warning(f"Suche '{query}' fehlgeschlagen: {e}")
            session.errors.append(f"{query}: {e}")
            session.queries_executed.append(query)

    logger.info(
        f"Web-Recherche abgeschlossen: {len(session.queries_executed)} Queries, "
        f"{len(session.results)} Ergebnisse, {len(session.errors)} Fehler"
    )
    return session
