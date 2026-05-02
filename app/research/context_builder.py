"""
Context Builder: Generiert Suchqueries und fasst Web-Ergebnisse
zu einem strukturierten MarketContext-Document zusammen.
"""
import json
import logging

from app.llm import LLMProvider, get_provider
from app.research.web_search import SearchSession

logger = logging.getLogger("simulator.research.context_builder")

# ---------------------------------------------------------------------------
# Tool-Definitionen
# ---------------------------------------------------------------------------

QUERY_GENERATION_TOOL_NAME = "search_queries"
QUERY_GENERATION_TOOL_DESC = "Generiert Suchbegriffe für die Marktrecherche"
QUERY_GENERATION_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "macro_queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 Suchbegriffe für Makro-Kontext (Wirtschaft, Politik, Gesellschaft des Zielmarkts)",
            "maxItems": 3,
        },
        "industry_queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 Suchbegriffe für Branchen-Kontext (aktuelle News, Wettbewerb, Regulierung)",
            "maxItems": 3,
        },
        "target_group_queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 Suchbegriffe für Zielgruppen-Kontext (Trends, Schmerzpunkte, Diskurse)",
            "maxItems": 3,
        },
    },
    "required": ["macro_queries", "industry_queries", "target_group_queries"],
}

CONTEXT_SYNTHESIS_TOOL_NAME = "market_context"
CONTEXT_SYNTHESIS_TOOL_DESC = "Strukturiertes Market-Context-Document"
CONTEXT_SYNTHESIS_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "macro_context": {
            "type": "string",
            "description": (
                "Makro-Kontext des Zielmarkts (200-400 Wörter, Markdown). "
                "Wirtschaftslage, politisches Klima, gesellschaftliche Stimmung, "
                "relevante Regulierungen. Konkret und aktuell."
            ),
        },
        "industry_context": {
            "type": "string",
            "description": (
                "Branchen-Kontext (200-400 Wörter, Markdown). "
                "Aktuelle Branchenentwicklungen, Wettbewerbssituation, "
                "regulatorische Veränderungen, Branchentrends. Mit konkreten Beispielen."
            ),
        },
        "target_group_context": {
            "type": "string",
            "description": (
                "Zielgruppen-Kontext (200-400 Wörter, Markdown). "
                "Aktuelle Schmerzpunkte, Trends, Diskursthemen, "
                "Stimmung gegenüber ähnlichen Produkten/Technologien. "
                "Welche Narrative dominieren gerade?"
            ),
        },
        "prompt_summary": {
            "type": "string",
            "description": (
                "Kompakte Zusammenfassung (max 300 Wörter) die direkt in Persona-Prompts "
                "eingefügt werden kann. Fokus auf: Was MUSS eine realistische Persona "
                "über die aktuelle Lage wissen? Welche Stimmungen und Debatten prägen "
                "gerade die öffentliche Meinung im Zielmarkt?"
            ),
        },
    },
    "required": ["macro_context", "industry_context", "target_group_context", "prompt_summary"],
}


async def generate_search_queries(
    product_description: str,
    target_market: str,
    industry: str,
    provider: LLMProvider | None = None,
    model: str | None = None,
) -> dict:
    """Generiert Suchqueries basierend auf Simulation-Parametern."""
    if provider is None:
        provider = get_provider(None)

    prompt = f"""Generiere präzise Web-Suchbegriffe für eine Marktrecherche.

Produkt: {product_description}
Zielmarkt: {target_market}
Branche: {industry}

Ziel: Aktuelle Lage des Zielmarkts verstehen, um realistische Personas zu generieren.

Regeln für Suchbegriffe:
- Deutsch oder Englisch je nach Zielmarkt
- Konkret und aktuell (z.B. "Wirtschaftslage Deutschland 2026" statt "Wirtschaft Deutschland")
- Branchenspezifisch (z.B. "MarTech Markt Europa Trends 2026")
- Zielgruppen-relevant (z.B. "CMO Herausforderungen B2B 2026")

Nutze das search_queries Tool."""

    result = await provider.call_tool(
        tier="fast",
        system="Du bist ein Research-Analyst. Generiere präzise Suchbegriffe.",
        cache_system=True,
        user_blocks=[{"text": prompt}],
        tool_name=QUERY_GENERATION_TOOL_NAME,
        tool_description=QUERY_GENERATION_TOOL_DESC,
        tool_schema=QUERY_GENERATION_TOOL_SCHEMA,
        max_tokens=4096,
        model=model,
    )

    return result


async def synthesize_context(
    product_description: str,
    target_market: str,
    industry: str,
    search_session: SearchSession,
    provider: LLMProvider | None = None,
    model: str | None = None,
) -> dict:
    """Fasst Web-Recherche-Ergebnisse zu einem MarketContext zusammen."""
    if provider is None:
        provider = get_provider(None)

    # Suchergebnisse aufbereiten
    search_data = []
    for r in search_session.results:
        search_data.append({
            "query": r.query,
            "title": r.title,
            "snippet": r.snippet,
            "url": r.url,
        })

    search_text = json.dumps(search_data, ensure_ascii=False, indent=2) if search_data else "Keine Ergebnisse gefunden."

    prompt = f"""Analysiere diese Web-Recherche-Ergebnisse und erstelle ein strukturiertes Market-Context-Document.

## Simulationskontext
Produkt: {product_description}
Zielmarkt: {target_market}
Branche: {industry}

## Web-Recherche-Ergebnisse
{search_text}

## Anweisungen
1. Fasse die Ergebnisse in drei Schichten zusammen: Makro, Branche, Zielgruppe
2. Sei KONKRET aber KURZ — max 150 Wörter pro Schicht
3. Wenn die Quellen wenig hergeben, ergänze mit deinem Wissen — markiere als "[LLM-Wissen]"
4. prompt_summary: MAX 200 Wörter, kompakt genug für einen Persona-Prompt
5. Fokus auf Faktoren die Persona-Verhalten beeinflussen
6. KEINE langen Einleitungen oder Zusammenfassungen — direkt die Fakten

Nutze das market_context Tool."""

    result = await provider.call_tool(
        tier="smart",
        system=(
            "Du bist ein Senior Market Research Analyst. "
            "Erstelle faktenbasierte Marktkontext-Dokumente auf Basis von Web-Recherche. "
            "Unterscheide klar zwischen Fakten aus Quellen und eigenem Wissen."
        ),
        cache_system=True,
        user_blocks=[{"text": prompt}],
        tool_name=CONTEXT_SYNTHESIS_TOOL_NAME,
        tool_description=CONTEXT_SYNTHESIS_TOOL_DESC,
        tool_schema=CONTEXT_SYNTHESIS_TOOL_SCHEMA,
        max_tokens=16000,
        model=model,
    )

    return result
