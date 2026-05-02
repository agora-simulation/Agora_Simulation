"""
Persona-Generierung via LLM-Provider (async) mit Tool Use.
Bei großen Persona-Mengen werden mehrere Batch-Calls parallel ausgeführt.
"""
import asyncio
import logging

from app.llm import LLMProvider, get_provider
from app.llm.resolver import ResolvedProvider

logger = logging.getLogger("simulator.persona_generator")

PERSONA_SYSTEM_PROMPT = """Du bist Experte für europäische Gesellschaftsforschung. \
Erstelle realistische, psychologisch tiefe Personas UND Organisationen/Institutionen. \
Min. 20% Skeptiker. Verwende Big-Five-Persönlichkeitstrait und realistische Demografie. \
Erzeuge einen realistischen Mix aus Einzelpersonen, Unternehmen, Institutionen und ggf. Politikern."""

BATCH_SIZE = 15
MAX_CONCURRENT_BATCHES = 2
_TOKENS_PER_PERSONA = 700
_BATCH_TOKEN_BUFFER = 2048

PERSONA_GENERATION_TOOL_NAME = "create_personas"
PERSONA_GENERATION_TOOL_DESC = "Erstellt eine Liste von Personas für die Marktsimulation"
PERSONA_GENERATION_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "personas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "string"},
                    "location": {"type": "string"},
                    "occupation": {"type": "string"},
                    "personality": {"type": "string", "description": "2-3 Sätze Charakterbeschreibung"},
                    "values": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                    "communication_style": {"type": "string"},
                    "initial_opinion": {"type": "string"},
                    "is_skeptic": {"type": "boolean"},
                    "preferred_platform": {
                        "type": "string",
                        "enum": ["feedbook", "threadit"],
                        "description": "feedbook = Facebook-ähnlich (emotional, Freundeslisten), threadit = Reddit-ähnlich (sachlich, Subreddits)",
                    },
                    "persona_type": {
                        "type": "string",
                        "enum": ["individual", "organization", "institution", "politician"],
                        "description": "Art des Akteurs. individual = Einzelperson, organization = Unternehmen/NGO/Verein, institution = Behoerde/Forschungseinrichtung/Pruefstelle, politician = Politiker/Parteivertreter",
                    },
                    "entity_subtype": {
                        "type": "string",
                        "description": "Spezifischer Subtyp, z.B. 'tech_startup', 'dax_konzern', 'handwerksbetrieb', 'verbraucherschutz', 'forschungsinstitut', 'gesundheitsamt', 'universitaet'. Nur fuer organization/institution/politician.",
                    },
                    "education_level": {
                        "type": "string",
                        "enum": ["Hauptschule", "Ausbildung", "Bachelor", "Master", "Promotion", "Sonstiges"],
                        "description": "Höchster Bildungsabschluss",
                    },
                    "income_bracket": {
                        "type": "string",
                        "enum": ["niedrig", "mittel", "hoch", "sehr_hoch"],
                        "description": "Einkommensklasse",
                    },
                    "family_status": {
                        "type": "string",
                        "enum": ["single", "partnerschaft", "familie_klein", "familie_gross", "alleinerziehend", "rentner"],
                        "description": "Familienstatus",
                    },
                    "political_leaning": {
                        "type": "string",
                        "enum": ["links", "mitte-links", "mitte", "mitte-rechts", "rechts", "unpolitisch"],
                        "description": "Politische Ausrichtung",
                    },
                    "media_consumption": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Medienkonsum, z.B. ['social_media', 'qualitaetspresse', 'boulevard', 'podcasts', 'tv']",
                    },
                    "tech_affinity": {
                        "type": "number",
                        "description": "Technik-Affinität 0.0 (technikfern) bis 1.0 (early adopter)",
                    },
                    "personality_traits": {
                        "type": "object",
                        "description": "Big Five Persönlichkeitsmodell, alle Werte 0.0-1.0",
                        "properties": {
                            "openness": {"type": "number", "description": "Offenheit für Erfahrungen 0.0-1.0"},
                            "conscientiousness": {"type": "number", "description": "Gewissenhaftigkeit 0.0-1.0"},
                            "extraversion": {"type": "number", "description": "Extraversion 0.0-1.0"},
                            "agreeableness": {"type": "number", "description": "Verträglichkeit 0.0-1.0"},
                            "neuroticism": {"type": "number", "description": "Neurotizismus 0.0-1.0"},
                        },
                        "required": ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"],
                    },
                },
                "required": [
                    "name", "age", "location", "occupation", "personality",
                    "values", "communication_style", "initial_opinion", "is_skeptic",
                    "preferred_platform", "education_level", "income_bracket",
                    "family_status", "political_leaning", "media_consumption",
                    "tech_affinity", "personality_traits", "persona_type",
                ],
            },
        }
    },
    "required": ["personas"],
}


def _build_prompt(
    product_description: str,
    target_market: str,
    industry: str,
    persona_count: int,
    batch_index: int = 0,
    batch_total: int = 1,
) -> str:
    batch_hint = ""
    if batch_total > 1:
        batch_hint = (
            f"\n\nDies ist Batch {batch_index + 1} von {batch_total}. "
            f"Erzeuge eigenständige, unverwechselbare Personas — verwende keine generischen "
            f"Namen wie 'Max Mustermann'. Nutze regional vielfältige Vornamen und Nachnamen."
        )

    diversity_requirements = """

WICHTIG für maximale Diversität und Realitätstreue:
- Alter: realistisch verteilt (18-80), nicht nur 25-45
  → Min. 15% über 55 Jahre, min. 10% unter 25 Jahre
- Bildung: von Hauptschule bis Promotion, realistisch verteilt
  → Min. 10% ohne Hochschulabschluss (Hauptschule oder Ausbildung)
- Einkommen: proportional zu Bildung/Beruf, aber mit Ausnahmen (Handwerker verdient gut)
- Familienstatus: Singles, Paare, Familien, Alleinerziehende, Rentner — alle vertreten
- Politisch: volle Bandbreite, nicht nur Mitte
- Tech-Affinität: vom Smartphone-Verweigerer (0.1) bis zum Developer (0.95)
- Big Five: realistische Verteilung, KEINE Durchschnittspersonen!
  → Extrem introvertierte (extraversion < 0.2), sehr gewissenhafte (> 0.8), neurotische (> 0.8)
  → Konfrontative (agreeableness < 0.2), sehr offene (openness > 0.8)
- Skeptiker: scharf und konsequent ablehnend — keine halbherzigen Skeptiker
- preferred_platform: gewissenhaftige/technikaffine/jüngere → threadit; emotionale/ältere → feedbook
- Akteur-Typen: Erzeuge einen realistischen Mix aus Einzelpersonen UND Organisationen/Institutionen!
  → Analysiere Produkt, Zielmarkt und Branche um die Gewichtung abzuleiten:
    - B2C-Konsumprodukt (z.B. Smartphone, Lebensmittel): ~75% individual, ~15% organization, ~10% institution
    - B2B-Fachprodukt (z.B. Laborgeräte, Industriesoftware): ~30-40% individual (Entscheider, Fachleute), ~40-50% organization (Firmen, Labore), ~15-25% institution (Behörden, Forschung, Prüfstellen)
    - Reguliertes Produkt (z.B. Medizin, Umwelt): Mehr Institutionen und Behörden einbeziehen
    - Wähle die Gewichtung passend zum konkreten Szenario — obige Zahlen sind Richtwerte, keine starren Regeln
  → Organisationen: age = Gründungsjahr (z.B. "2019"), occupation = Branche/Rolle
  → entity_subtype MUSS spezifisch und zur Branche passend sein
  → Beispiel Medizinprodukt: Pharma-Konzern, Gesundheitsamt, Verbraucherzentrale, Uni-Klinik
  → Beispiel Laborgerät: Umweltlabor, Forschungsinstitut, kommunales Wasserlabor, Auftragslabor, TÜV
  → Beispiel Tech-Produkt: Tech-Startup, Datenschutzverein, TÜV, Fraunhofer-Institut
  → Organisationen posten offizieller/sachlicher als Einzelpersonen
  → Einzelpersonen bei B2B = Laborleiter, Forscher, Einkäufer, Techniker — NICHT zufällige Bürger"""

    return f"""Produkt/Idee: {product_description}
Zielmarkt: {target_market}
Branche: {industry}

Erstelle {persona_count} diverse Akteure für diese Marktsimulation.
Analysiere zuerst Produkt, Zielmarkt und Branche: Ist es B2C oder B2B? Wer sind die \
realen Stakeholder? Erzeuge dann einen passenden Mix aus Einzelpersonen, Organisationen \
und Institutionen — die Gewichtung MUSS zum Szenario passen.
Europäische Gesellschaftsrealität (DE/AT/CH): politische Fragmentierung, Datenskepsis, \
regionale Unterschiede. Inkludiere Zielgruppen, Randfälle und Skeptiker/Gegner \
(mindestens 20% der Akteure müssen is_skeptic=true sein).

Jede Persona braucht:
- name (string)
- age (string, z.B. "34")
- location (string, z.B. "München", "Wien", "Zürich", "Hamburg", "Bern")
- occupation (string)
- personality (string, 2-3 Sätze Charakterbeschreibung)
- values (array of strings, max 5 Kernwerte)
- communication_style (string, 1-2 Sätze wie diese Person schreibt/spricht)
- initial_opinion (string, erste Haltung zum Produkt)
- is_skeptic (boolean)
- preferred_platform ("feedbook" oder "threadit") — welche Plattform passt zum Charakter? \
Jüngere/technikaffine/sachliche Typen → threadit; emotionale/familienorientierte/ältere Typen → feedbook. \
Verteile realistisch: ca. 55% feedbook, 45% threadit.{diversity_requirements}{batch_hint}"""


async def _generate_batch(
    provider: LLMProvider,
    product_description: str,
    target_market: str,
    industry: str,
    persona_count: int,
    batch_index: int,
    batch_total: int,
    semaphore: asyncio.Semaphore,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> list[dict]:
    async with semaphore:
        prompt = _build_prompt(
            product_description, target_market, industry,
            persona_count, batch_index, batch_total,
        )
        max_tokens = max(4096, persona_count * _TOKENS_PER_PERSONA + _BATCH_TOKEN_BUFFER)

        result = await provider.call_tool(
            tier="smart",
            system=PERSONA_SYSTEM_PROMPT,
            cache_system=True,
            user_blocks=[{"text": prompt}],
            tool_name=PERSONA_GENERATION_TOOL_NAME,
            tool_description=PERSONA_GENERATION_TOOL_DESC,
            tool_schema=PERSONA_GENERATION_TOOL_SCHEMA,
            max_tokens=max_tokens,
            model=model,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )

        personas = result.get("personas") if isinstance(result, dict) else None
        if not personas:
            raise RuntimeError(
                f"Persona-Generator (Batch {batch_index + 1}/{batch_total}): "
                f"Antwort enthält kein 'personas'-Feld (max_tokens={max_tokens})."
            )

        # Wenn das Modell weniger als angefordert liefert: einmal nachfordern
        if len(personas) < persona_count:
            missing = persona_count - len(personas)
            logger.warning(
                "Persona-Batch %d/%d: nur %d/%d Personas erhalten — fordere %d nach",
                batch_index + 1, batch_total, len(personas), persona_count, missing,
            )
            retry_prompt = _build_prompt(
                product_description, target_market, industry,
                missing, batch_index, batch_total,
            )
            retry_max_tokens = max(4096, missing * _TOKENS_PER_PERSONA + _BATCH_TOKEN_BUFFER)
            try:
                retry_result = await provider.call_tool(
                    tier="smart",
                    system=PERSONA_SYSTEM_PROMPT,
                    cache_system=True,
                    user_blocks=[{"text": retry_prompt}],
                    tool_name=PERSONA_GENERATION_TOOL_NAME,
                    tool_description=PERSONA_GENERATION_TOOL_DESC,
                    tool_schema=PERSONA_GENERATION_TOOL_SCHEMA,
                    max_tokens=retry_max_tokens,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                )
                extra = retry_result.get("personas") if isinstance(retry_result, dict) else None
                if extra:
                    personas.extend(extra)
                    logger.info("Nachforderung erfolgreich: +%d Personas", len(extra))
            except Exception as e:
                logger.warning("Nachforderung fehlgeschlagen (akzeptiere Teilergebnis): %s", e)

        logger.info(
            "Persona-Batch %d/%d fertig: %d Personas",
            batch_index + 1, batch_total, len(personas),
        )
        return personas


def _dedupe_names(personas: list[dict]) -> list[dict]:
    """Eindeutige Namen via Suffix-Counter (Anna Schmidt, Anna Schmidt 2, ...)."""
    seen: dict[str, int] = {}
    for p in personas:
        original = (p.get("name") or "").strip() or "Persona"
        key = original.lower()
        if key not in seen:
            seen[key] = 1
            p["name"] = original
        else:
            seen[key] += 1
            p["name"] = f"{original} {seen[key]}"
    return personas


async def generate_personas(
    product_description: str,
    target_market: str,
    industry: str,
    persona_count: int = 10,
    provider_name: str | None = None,
    model: str | None = None,
    resolved: ResolvedProvider | None = None,
    sim=None,
    db=None,
) -> list[dict]:
    """Generiert N Personas asynchron via konfigurierten LLM-Provider.

    Bei persona_count > BATCH_SIZE werden mehrere Batches parallel ausgeführt
    (max. MAX_CONCURRENT_BATCHES gleichzeitig).

    sim + db: Wenn gesetzt, wird pro Batch neu resolved (Multi-Provider-Support).
    resolved: Legacy — ein fester Provider für alle Batches.
    """
    # Helper: Provider pro Batch resolven (Multi-Provider bei Weighted-Random)
    async def _resolve_once():
        if sim and db:
            from app.llm.resolver import resolve_for_phase
            return await resolve_for_phase(sim, "persona_generation", db)
        if resolved:
            return resolved
        return ResolvedProvider(
            provider=get_provider(provider_name),
            model=model,
            temperature=None, top_p=None, top_k=None,
        )

    first_resolved = await _resolve_once()
    logger.info(
        "Starte Persona-Generierung (%d Personas, provider=%s)",
        persona_count, first_resolved.provider.name,
    )

    if persona_count <= BATCH_SIZE:
        result = await _generate_batch(
            first_resolved.provider, product_description, target_market, industry,
            persona_count, batch_index=0, batch_total=1,
            semaphore=asyncio.Semaphore(1),
            model=first_resolved.model,
            temperature=first_resolved.temperature,
            top_p=first_resolved.top_p, top_k=first_resolved.top_k,
        )
        result = _dedupe_names(result)
        logger.info("Persona-Generierung abgeschlossen: %d Personas erstellt", len(result))
        return result

    # Aufteilung in Batches
    batch_sizes: list[int] = []
    remaining = persona_count
    while remaining > 0:
        size = min(BATCH_SIZE, remaining)
        batch_sizes.append(size)
        remaining -= size

    batch_total = len(batch_sizes)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

    logger.info(
        "Persona-Generierung in %d Batches à ~%d (max %d parallel)",
        batch_total, BATCH_SIZE, MAX_CONCURRENT_BATCHES,
    )

    # Pro Batch neu resolven → bei 50/50 Gewichtung werden unterschiedliche Provider genutzt
    async def _run_batch(idx: int, size: int):
        r = await _resolve_once()
        logger.info("Batch %d/%d → provider=%s, model=%s", idx + 1, batch_total, r.provider.name, r.model)
        return await _generate_batch(
            r.provider, product_description, target_market, industry,
            size, idx, batch_total, semaphore,
            model=r.model,
            temperature=r.temperature, top_p=r.top_p, top_k=r.top_k,
        )

    tasks = [_run_batch(idx, size) for idx, size in enumerate(batch_sizes)]
    batch_results = await asyncio.gather(*tasks)

    all_personas: list[dict] = []
    for batch in batch_results:
        all_personas.extend(batch)

    all_personas = _dedupe_names(all_personas)

    if len(all_personas) < persona_count:
        logger.warning(
            "Persona-Generierung lieferte %d von %d angeforderten Personas",
            len(all_personas), persona_count,
        )
    elif len(all_personas) > persona_count:
        all_personas = all_personas[:persona_count]

    logger.info("Persona-Generierung abgeschlossen: %d Personas erstellt", len(all_personas))
    return all_personas
