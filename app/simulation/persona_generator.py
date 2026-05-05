"""
Persona-Generierung via Hybrid-Architektur (Option C):

Phase 1: Ein LLM-Call generiert eine Skelett-Matrix (Name, Alter, Beruf, Typ, etc.)
         → Kompaktes JSON, ~50 Tokens pro Persona → skaliert bis 500+
Phase 2: Pro Persona ein einzelner LLM-Call für Persönlichkeit, Big Five, Werte
         → ~400 Tokens Output pro Call → kann nicht am Token-Limit scheitern
         → Massiv parallel (bis 15 gleichzeitig)

Personas werden gegen DACH-Demographie und Rogers Diffusion validiert.
"""
import asyncio
import json
import logging
import random as _random

from app.llm import LLMProvider, get_provider
from app.llm.resolver import ResolvedProvider

logger = logging.getLogger("agora.persona_generator")


# ---------------------------------------------------------------------------
# Rogers Diffusion of Innovation — Verteilung für Persona-Kalibrierung
# ---------------------------------------------------------------------------

ROGERS_DISTRIBUTION = {
    "innovator": 0.025,
    "early_adopter": 0.135,
    "early_majority": 0.34,
    "late_majority": 0.34,
    "laggard": 0.16,
}

DACH_AGE_DISTRIBUTION = {
    "18-24": 0.08, "25-34": 0.15, "35-44": 0.16,
    "45-54": 0.18, "55-64": 0.18, "65-80": 0.25,
}

DACH_EDUCATION_DISTRIBUTION = {
    "Hauptschule": 0.15, "Ausbildung": 0.35, "Bachelor": 0.15,
    "Master": 0.20, "Promotion": 0.08, "Sonstiges": 0.07,
}

MAX_CONCURRENT_ENRICH = 10  # Parallele Enrichment-Calls
MAX_CONCURRENT_SKELETON = 10  # Parallele Skelett-Calls
SKELETON_BATCH_SIZE = 3     # Max Personas pro Skelett-Call — GPT-5 ist extrem verbose


# ---------------------------------------------------------------------------
# Phase 1: Skelett-Generierung (kompakt, skalierbar)
# ---------------------------------------------------------------------------

SKELETON_TOOL_NAME = "create_persona_skeletons"
SKELETON_TOOL_DESC = "Erstellt kompakte Persona-Skelette für die Marktsimulation"
SKELETON_TOOL_SCHEMA = {
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
                    "is_skeptic": {"type": "boolean"},
                    "actor_type": {
                        "type": "string",
                        "enum": ["private_person", "company", "research_institute", "authority", "media", "influencer", "expert", "collective", "validator"],
                    },
                    "subtype": {"type": "string"},
                    "context": {"type": "string", "enum": ["privat", "beruflich", "oeffentlich", "consumer", "business", "politisch"]},
                    "traegerschaft": {"type": "string", "enum": ["privat", "oeffentlich", "genossenschaftlich", "gemischt", "kommunal"]},
                    "stance": {"type": "string"},
                    "activation_latency": {"type": "integer"},
                    "entity_subtype": {"type": "string"},
                    "preferred_platform": {
                        "type": "string",
                        "enum": ["feedbook", "threadit"],
                    },
                    "education_level": {
                        "type": "string",
                        "enum": ["Hauptschule", "Ausbildung", "Bachelor", "Master", "Promotion", "Sonstiges"],
                    },
                    "income_bracket": {
                        "type": "string",
                        "enum": ["niedrig", "mittel", "hoch", "sehr_hoch"],
                    },
                    "tech_affinity": {"type": "number"},
                    "discussion_role": {
                        "type": "string",
                        "enum": ["opinion_leader", "engaged", "follower", "quiet", "contrarian", "showboat"],
                    },
                    "rogers_category": {
                        "type": "string",
                        "enum": ["innovator", "early_adopter", "early_majority", "late_majority", "laggard"],
                    },
                    "formality_level": {"type": "integer", "minimum": 1, "maximum": 5},
                    "regional_dialect": {
                        "type": "string",
                        "enum": ["norddeutsch", "bayerisch", "berlinerisch", "oesterreichisch", "schweizerdeutsch", "neutral"],
                    },
                    "b2b_b2c_mode": {"type": "string", "enum": ["b2b", "b2c"]},
                },
                "required": ["name", "age", "location", "occupation", "is_skeptic",
                             "actor_type", "preferred_platform", "education_level",
                             "income_bracket", "tech_affinity",
                             "discussion_role", "rogers_category", "formality_level",
                             "regional_dialect"],
            },
        }
    },
    "required": ["personas"],
}

# Backwards compatibility mapping
_OLD_TYPE_MAPPING = {
    "individual": "private_person",
    "organization": "company",
    "institution": "collective",
    "politician": "private_person",
}

SKELETON_SYSTEM_PROMPT = """Du bist Experte für europäische Gesellschaftsforschung und Marktdynamik.
Erstelle kompakte Persona-Skelette für die Marktsimulation.
Halte die Antworten KURZ — nur die geforderten Felder, keine zusätzlichen Texte.

Die 9 AKTEURS-TYPEN:
1. private_person — Einzelperson (context: privat/beruflich/oeffentlich)
2. company — Organisation mit Marktinteresse (traegerschaft: privat/oeffentlich/genossenschaftlich/gemischt/kommunal)
3. research_institute — Wissenschaftliche Einrichtung
4. authority — Behörde/Regulator
5. media — Medium/Journalist
6. influencer — Reichweiten-Einzelperson (context: consumer/business/politisch)
7. expert — Domänen-Autorität
8. collective — Verband/NGO/Partei/Kammer/Stiftung (subtype angeben)
9. validator — Prüfstelle/Zertifizierer (subtype: tuev/behoerdliche_pruefstelle/versicherer/norm_setter)

DISKUSSIONSROLLEN (jede Persona bekommt genau eine):
- opinion_leader (10-15%): Spricht zuerst, rahmt die Diskussion
- engaged (30-40%): Aktiv, baut auf anderen auf
- follower (25-35%): Stimmt Mehrheit zu, kurz
- quiet (10-20%): Spricht nur wenn angesprochen
- contrarian (5-10%): Stellt Konsens in Frage
- showboat (3-5%): Off-topic, monopolisiert

ROGERS DIFFUSION: innovator 2.5%, early_adopter 13.5%, early_majority 34%, late_majority 34%, laggard 16%
Korreliert mit tech_affinity: Innovatoren >0.8, Laggards <0.2.

REGIONALE DIALEKTE (DACH): norddeutsch, bayerisch, berlinerisch, oesterreichisch, schweizerdeutsch, neutral
Wähle passend zum Standort. ~40% neutral, Rest verteilt nach Region.

FORMALITÄTS-LEVEL 1-5: Korreliert mit Alter und Bildung.
1 = sehr salopp (Gen Z), 2 = locker, 3 = normal, 4 = formell, 5 = sehr formell (Boomer/Akademiker).

activation_latency (Tage bis aktiv): Privatpersonen 0-1, Firmen 1-3, Institute 5-10,
Behörden 7-15, Medien 1-4, Influencer 0-2, Experten 2-5, Kollektive 3-7, Validierer 10-20.
stance passend zum Typ (z.B. Firma: potential_buyer/competitor/supplier/observer).
DACH-Demographie: Alter 18-80 realistisch verteilt."""


def _build_skeleton_prompt(
    product_description: str,
    target_market: str,
    industry: str,
    persona_count: int,
    batch_index: int = 0,
    batch_total: int = 1,
    market_context_summary: str | None = None,
    distribution_template: dict | None = None,
) -> str:
    market_block = ""
    if market_context_summary:
        market_block = f"\n\nAktuelle Marktlage:\n{market_context_summary}\n"

    batch_hint = ""
    if batch_total > 1:
        batch_hint = f"\nDies ist Batch {batch_index + 1}/{batch_total}. Keine Duplikate zu anderen Batches!"

    distribution_block = ""
    if distribution_template:
        dist_lines = [f"- {k}: {v}%" for k, v in distribution_template.items() if v > 0]
        distribution_block = "\n\nAkteurs-Verteilung:\n" + "\n".join(dist_lines)

    return f"""Produkt: {product_description}
Zielmarkt: {target_market}
Branche: {industry}
{market_block}{distribution_block}
Erstelle {persona_count} KOMPAKTE Persona-Skelette.
Nur Basisdaten — Persönlichkeit wird separat generiert.
Min. 20% Skeptiker. Mix der 9 Akteurs-Typen passend zur Branche und Verteilung.
Vielfältige Namen (DACH-Region), keine generischen Namen.{batch_hint}"""


async def _generate_skeletons(
    provider: LLMProvider,
    product_description: str,
    target_market: str,
    industry: str,
    persona_count: int,
    batch_index: int,
    batch_total: int,
    model: str | None = None,
    market_context_summary: str | None = None,
    distribution_template: dict | None = None,
) -> list[dict]:
    """Phase 1: Generiert kompakte Skelette. ~50 Tokens pro Persona Output."""
    prompt = _build_skeleton_prompt(
        product_description, target_market, industry,
        persona_count, batch_index, batch_total,
        market_context_summary, distribution_template,
    )
    # ~50 Tokens pro Persona + Buffer
    # ~120 Tokens pro Skelett (GPT-5 ist verbose) + Buffer
    # GPT-5 braucht ~200-300 Tokens pro Skelett (extrem verbose)
    max_tokens = max(8192, persona_count * 300 + 2000)

    try:
        result = await provider.call_tool(
            tier="smart",
            system=SKELETON_SYSTEM_PROMPT,
            cache_system=True,
            user_blocks=[{"text": prompt}],
            tool_name=SKELETON_TOOL_NAME,
            tool_description=SKELETON_TOOL_DESC,
            tool_schema=SKELETON_TOOL_SCHEMA,
            max_tokens=max_tokens,
            model=model,
        )
        personas = result.get("personas") if isinstance(result, dict) else None
        if not personas:
            logger.error("Skelett-Batch %d/%d: keine Personas erhalten", batch_index + 1, batch_total)
            return []
        logger.info("Skelett-Batch %d/%d: %d Skelette generiert", batch_index + 1, batch_total, len(personas))
        return personas
    except Exception as e:
        logger.error("Skelett-Batch %d/%d fehlgeschlagen: %s", batch_index + 1, batch_total, e)
        return []


# ---------------------------------------------------------------------------
# Phase 2: Persönlichkeits-Anreicherung (1 Call pro Persona, parallel)
# ---------------------------------------------------------------------------

ENRICH_TOOL_NAME = "enrich_persona"
ENRICH_TOOL_DESC = "Ergänzt eine Persona um Persönlichkeit, Werte und Meinung"
ENRICH_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "personality": {"type": "string", "description": "2-3 Sätze Charakterbeschreibung"},
        "values": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "communication_style": {"type": "string", "description": "1-2 Sätze Kommunikationsstil"},
        "initial_opinion": {"type": "string", "description": "Erste Haltung zum Produkt"},
        "family_status": {
            "type": "string",
            "enum": ["single", "partnerschaft", "familie_klein", "familie_gross", "alleinerziehend", "rentner"],
        },
        "political_leaning": {
            "type": "string",
            "enum": ["links", "mitte-links", "mitte", "mitte-rechts", "rechts", "unpolitisch"],
        },
        "media_consumption": {
            "type": "array", "items": {"type": "string"},
        },
        "personality_traits": {
            "type": "object",
            "properties": {
                "openness": {"type": "number"},
                "conscientiousness": {"type": "number"},
                "extraversion": {"type": "number"},
                "agreeableness": {"type": "number"},
                "neuroticism": {"type": "number"},
            },
            "required": ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"],
        },
        # Realism Overhaul: neue Enrichment-Felder
        "response_length_tendency": {
            "type": "string",
            "enum": ["one_liner", "medium", "detailed"],
            "description": "Antwort-Tendenz: 35% one_liner, 40% medium, 25% detailed",
        },
        "noise_propensity": {
            "type": "number",
            "minimum": 0, "maximum": 1,
            "description": "Off-Topic-Wahrscheinlichkeit (0-1, Realität: 0.15-0.30)",
        },
        "acquiescence_bias": {
            "type": "number",
            "minimum": 0, "maximum": 1,
            "description": "Ja-Sager-Tendenz (0-1, Realität: 0.10-0.20)",
        },
        "survey_fatigue_rate": {
            "type": "number",
            "minimum": 0, "maximum": 1,
            "description": "Ermüdungsrate (0-1, wie schnell die Antwortqualität sinkt)",
        },
        "verbal_tics": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
            "description": "1-3 Sprachmarotten (z.B. 'quasi', 'im Endeffekt', 'sage ich mal')",
        },
        "internal_contradictions": {
            "type": "string",
            "description": "1 realistischer Widerspruch in den Ansichten dieser Person",
        },
    },
    "required": ["personality", "values", "communication_style", "initial_opinion",
                 "family_status", "political_leaning", "media_consumption", "personality_traits",
                 "response_length_tendency", "noise_propensity", "acquiescence_bias",
                 "survey_fatigue_rate", "verbal_tics", "internal_contradictions"],
}

ENRICH_SYSTEM_PROMPT = """Du bist KEIN KI-Assistent. Du erschaffst eine ECHTE Person mit Macken, Widersprüchen und Eigenheiten.

Erstelle eine realistische, EINZIGARTIGE Persönlichkeit. Jede Person muss sich deutlich von anderen unterscheiden.

DIVERSITÄTS-REGELN:
- personality: 2-3 Sätze, die DIESE Person unverwechselbar machen. Keine generischen Phrasen.
- communication_style: 1 Satz. Variiere stark: emotional/sachlich/provokant/zurückhaltend/akademisch/umgangssprachlich.
- initial_opinion: 1 Satz. Skeptiker = KLAR ablehnend mit konkretem Grund. Befürworter = spezifischer Enthusiasmus, nicht "offen für Neues".
- values: 3-5 SPEZIFISCHE Werte (nicht "Pragmatismus" oder "Innovation" — sondern z.B. "Bodenschutz", "Familienbetrieb erhalten", "Kostenwahrheit").
- Big Five: Extreme nutzen! Nicht alles bei 0.4-0.6. Introvertierte (E<0.2), Konfrontative (A<0.2), Neurotische (N>0.8) sind realistisch.
- political_leaning: Volle Bandbreite, nicht nur "mitte".
- media_consumption: Realistisch zur Person (68-Jährige liest Tageszeitung, nicht TikTok).

ANTWORT-VERHALTEN (realistische Marktforschung):
- response_length_tendency: 35% one_liner, 40% medium, 25% detailed. Wähle passend zur Person.
- noise_propensity (0-1): Wie oft geht die Person off-topic? Realität: 15-30%. Extrovertierte & Showboats höher.
- acquiescence_bias (0-1): Ja-Sager-Tendenz. Realität: 10-20%. Follower höher, Contrarians niedriger.
- survey_fatigue_rate (0-1): Wie schnell ermüdet die Person? Jüngere und Desinteressierte schneller.
- verbal_tics: 1-3 KONKRETE Sprachmarotten. Z.B. "quasi", "im Endeffekt", "sage ich mal", "halt", "sozusagen", "an und für sich", "jetzt mal ehrlich", "also ich muss sagen".
- internal_contradictions: 1 KONKRETER Widerspruch. Z.B. "Ist für Umweltschutz, fliegt aber 3x im Jahr in den Urlaub" oder "Fordert Datenschutz, nutzt aber alle Social-Media-Plattformen".

HALTE DICH KURZ. Keine langen Erklärungen."""


async def _enrich_persona(
    provider: LLMProvider,
    skeleton: dict,
    product_description: str,
    semaphore: asyncio.Semaphore,
    model: str | None = None,
    market_context_summary: str | None = None,
) -> dict:
    """Phase 2: Reichert ein einzelnes Skelett mit Persönlichkeit an. ~400 Tokens Output."""
    actor_type = skeleton.get("actor_type", skeleton.get("persona_type", "private_person"))
    # Backwards compat
    if actor_type in _OLD_TYPE_MAPPING:
        actor_type = _OLD_TYPE_MAPPING[actor_type]
    skeptic_hint = "Du bist SKEPTISCH — deine initiale Meinung ist ablehnend/kritisch." if skeleton.get("is_skeptic") else ""

    if actor_type == "private_person":
        context = skeleton.get("context", "privat")
        identity = f"{skeleton['name']}, {skeleton['age']} Jahre, {skeleton['location']}, {skeleton['occupation']} (Kontext: {context})"
    elif actor_type == "company":
        subtype = skeleton.get("subtype", skeleton.get("entity_subtype", "Unternehmen"))
        traeg = skeleton.get("traegerschaft", "privat")
        identity = f"{skeleton['name']} ({subtype}), {skeleton['location']}, Trägerschaft: {traeg}"
    elif actor_type == "research_institute":
        identity = f"{skeleton['name']} (Forschungsinstitut), {skeleton['location']}"
    elif actor_type == "authority":
        identity = f"{skeleton['name']} (Behörde/Regulator), {skeleton['location']}"
    elif actor_type == "media":
        identity = f"{skeleton['name']} (Medium/Journalist), {skeleton['location']}"
    elif actor_type == "influencer":
        context = skeleton.get("context", "consumer")
        identity = f"{skeleton['name']} (Influencer, {context}), Reichweite: {skeleton.get('occupation', 'Social Media')}"
    elif actor_type == "expert":
        identity = f"{skeleton['name']} (Experte), {skeleton['location']}, Domäne: {skeleton['occupation']}"
    elif actor_type == "collective":
        subtype = skeleton.get("subtype", skeleton.get("entity_subtype", "Verband"))
        identity = f"{skeleton['name']} ({subtype}), {skeleton['location']}"
    elif actor_type == "validator":
        subtype = skeleton.get("subtype", skeleton.get("entity_subtype", "Prüfstelle"))
        identity = f"{skeleton['name']} ({subtype}), {skeleton['location']}"
    else:
        identity = f"{skeleton['name']}, {skeleton['age']} Jahre, {skeleton['location']}, {skeleton['occupation']}"

    market_hint = f"\nAktuelle Marktlage: {market_context_summary[:300]}" if market_context_summary else ""

    prompt = f"""Person: {identity}
Bildung: {skeleton.get('education_level', 'k.A.')} | Einkommen: {skeleton.get('income_bracket', 'k.A.')}
Tech-Affinität: {skeleton.get('tech_affinity', 0.5)} | Typ: {actor_type}
{skeptic_hint}

Produkt: {product_description[:200]}
{market_hint}

Erstelle Persönlichkeit, Werte, Kommunikationsstil, initiale Meinung, Familienstatus,
politische Ausrichtung, Medienkonsum und Big-Five-Traits. Nutze das enrich_persona Tool."""

    async with semaphore:
        try:
            result = await provider.call_tool(
                tier="smart",
                system=ENRICH_SYSTEM_PROMPT,
                cache_system=True,
                user_blocks=[{"text": prompt}],
                tool_name=ENRICH_TOOL_NAME,
                tool_description=ENRICH_TOOL_DESC,
                tool_schema=ENRICH_TOOL_SCHEMA,
                max_tokens=4096,
                model=model,
            )
            # Skelett + Enrichment zusammenführen
            merged = {**skeleton, **result}
            return merged
        except Exception as e:
            logger.warning("Enrichment für %s fehlgeschlagen: %s — verwende Fallback", skeleton.get("name"), e)
            # Fallback: Skelett mit Minimal-Persönlichkeit
            return {
                **skeleton,
                "personality": f"{skeleton.get('occupation', 'Person')} aus {skeleton.get('location', 'DACH')}.",
                "values": ["Pragmatismus"],
                "communication_style": "Sachlich und direkt.",
                "initial_opinion": "Abwartend." if skeleton.get("is_skeptic") else "Offen für Neues.",
                "family_status": "single",
                "political_leaning": "mitte",
                "media_consumption": ["social_media"],
                "personality_traits": {
                    "openness": 0.3 if skeleton.get("is_skeptic") else 0.6,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.4,
                },
            }


# ---------------------------------------------------------------------------
# Validierung (unverändert)
# ---------------------------------------------------------------------------

def _classify_adopter_type(persona: dict) -> str:
    tech = persona.get("tech_affinity", 0.5)
    openness = (persona.get("personality_traits") or {}).get("openness", 0.5)
    is_skeptic = persona.get("is_skeptic", False)
    innovation_score = (tech * 0.5 + openness * 0.3 + (0.0 if is_skeptic else 0.2))
    if innovation_score > 0.85: return "innovator"
    elif innovation_score > 0.65: return "early_adopter"
    elif innovation_score > 0.45: return "early_majority"
    elif innovation_score > 0.25: return "late_majority"
    else: return "laggard"


DISCUSSION_ROLE_DISTRIBUTION = {
    "opinion_leader": 0.12, "engaged": 0.35, "follower": 0.30,
    "quiet": 0.15, "contrarian": 0.05, "showboat": 0.03,
}


def _validate_and_adjust_personas(personas: list[dict], target_count: int) -> list[dict]:
    if not personas:
        return personas
    n = len(personas)

    # Rogers Diffusion Check
    adopter_counts = {k: 0 for k in ROGERS_DISTRIBUTION}
    for p in personas:
        adopter_counts[_classify_adopter_type(p)] += 1
    for category, target_pct in ROGERS_DISTRIBUTION.items():
        actual_pct = adopter_counts[category] / n
        if abs(actual_pct - target_pct) > 0.1:
            logger.warning(f"Rogers: {category} = {adopter_counts[category]}/{n} ({actual_pct:.0%}), Soll: {target_pct:.0%}")

    # Skeptiker-Quote
    skeptic_count = sum(1 for p in personas if p.get("is_skeptic"))
    if skeptic_count / n < 0.20:
        logger.warning(f"Skeptiker-Quote zu niedrig: {skeptic_count / n:.0%}")
        non_skeptics = [p for p in personas if not p.get("is_skeptic")]
        non_skeptics.sort(key=lambda p: (p.get("personality_traits") or {}).get("openness", 0.5))
        for p in non_skeptics[:int(0.20 * n) - skeptic_count]:
            p["is_skeptic"] = True

    # Diskussionsrollen-Verteilung prüfen und nachrüsten
    role_counts = {}
    no_role = []
    for p in personas:
        role = p.get("discussion_role")
        if role and role in DISCUSSION_ROLE_DISTRIBUTION:
            role_counts[role] = role_counts.get(role, 0) + 1
        else:
            no_role.append(p)

    # Fehlende Rollen zuweisen
    if no_role:
        from app.simulation.discussion_roles import assign_discussion_role
        for p in no_role:
            p["discussion_role"] = assign_discussion_role(p)
        logger.info(f"Diskussionsrollen nachgerüstet für {len(no_role)} Personas")

    # Regionale Dialekt-Verteilung prüfen (~40% neutral)
    dialect_counts = {}
    for p in personas:
        d = p.get("regional_dialect", "neutral")
        dialect_counts[d] = dialect_counts.get(d, 0) + 1
    neutral_pct = dialect_counts.get("neutral", 0) / n
    if neutral_pct < 0.25:
        logger.warning(f"Nur {neutral_pct:.0%} neutral-Dialekt (Soll: ~40%)")

    # Formality-Level Verteilung (Normalverteilung um 3)
    formality_values = [p.get("formality_level", 3) for p in personas]
    avg_formality = sum(formality_values) / n
    if abs(avg_formality - 3.0) > 1.0:
        logger.warning(f"Formality-Level Durchschnitt = {avg_formality:.1f} (Soll: ~3.0)")

    return personas


def _dedupe_names(personas: list[dict]) -> list[dict]:
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


# ---------------------------------------------------------------------------
# Hauptfunktion: Hybrid-Generierung
# ---------------------------------------------------------------------------

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
    market_context_summary: str | None = None,
    distribution_template: dict | None = None,
) -> list[dict]:
    """Generiert N Personas via Hybrid-Architektur (Option C).

    Phase 1: Skelett-Matrix (kompakt, in Batches à 50)
    Phase 2: Persönlichkeits-Anreicherung (1 Call pro Persona, massiv parallel)
    """
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
        "Starte Persona-Generierung (%d Personas, provider=%s) — Hybrid-Modus",
        persona_count, first_resolved.provider.name,
    )

    # === Phase 1: Skelett-Generierung (parallel, kleine Batches) ===
    batch_count = (persona_count + SKELETON_BATCH_SIZE - 1) // SKELETON_BATCH_SIZE
    logger.info(
        "Phase 1: Skelett-Matrix generieren (%d angefordert, %d Batches à %d, max %d parallel)",
        persona_count, batch_count, SKELETON_BATCH_SIZE, MAX_CONCURRENT_SKELETON,
    )

    skeleton_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SKELETON)

    async def _skeleton_batch(idx: int, size: int) -> list[dict]:
        async with skeleton_semaphore:
            r = await _resolve_once()
            return await _generate_skeletons(
                r.provider, product_description, target_market, industry,
                size, idx, batch_count,
                model=r.model,
                market_context_summary=market_context_summary,
                distribution_template=distribution_template,
            )

    # Batches aufteilen
    batch_sizes: list[int] = []
    remaining = persona_count
    while remaining > 0:
        batch_sizes.append(min(SKELETON_BATCH_SIZE, remaining))
        remaining -= SKELETON_BATCH_SIZE

    # Alle Batches parallel starten
    skeleton_results = await asyncio.gather(
        *[_skeleton_batch(i, size) for i, size in enumerate(batch_sizes)],
        return_exceptions=True,
    )

    all_skeletons: list[dict] = []
    for i, result in enumerate(skeleton_results):
        if isinstance(result, Exception):
            logger.warning("Skelett-Batch %d fehlgeschlagen: %s", i + 1, result)
        elif isinstance(result, list):
            all_skeletons.extend(result)

    all_skeletons = _dedupe_names(all_skeletons)
    if len(all_skeletons) > persona_count:
        all_skeletons = all_skeletons[:persona_count]

    # v1.1: Backwards compat — map old persona_type to actor_type
    for skeleton in all_skeletons:
        if "persona_type" in skeleton and "actor_type" not in skeleton:
            old_type = skeleton.pop("persona_type")
            skeleton["actor_type"] = _OLD_TYPE_MAPPING.get(old_type, "private_person")
        elif "actor_type" not in skeleton:
            skeleton["actor_type"] = "private_person"

    logger.info("Phase 1 abgeschlossen: %d/%d Skelette generiert", len(all_skeletons), persona_count)

    if not all_skeletons:
        logger.error("Keine Skelette generiert — Abbruch")
        return []

    # === Phase 2: Persönlichkeits-Anreicherung (parallel) ===
    logger.info("Phase 2: %d Personas anreichern (max %d parallel)", len(all_skeletons), MAX_CONCURRENT_ENRICH)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_ENRICH)

    async def _enrich_one(skeleton: dict) -> dict:
        r = await _resolve_once()
        return await _enrich_persona(
            r.provider, skeleton, product_description, semaphore,
            model=r.model,
            market_context_summary=market_context_summary,
        )

    enriched = await asyncio.gather(
        *[_enrich_one(s) for s in all_skeletons],
        return_exceptions=True,
    )

    # Exceptions filtern
    all_personas: list[dict] = []
    for i, result in enumerate(enriched):
        if isinstance(result, Exception):
            logger.warning("Enrichment %d fehlgeschlagen: %s — übersprungen", i, result)
        elif isinstance(result, dict):
            all_personas.append(result)

    all_personas = _dedupe_names(all_personas)

    if len(all_personas) < persona_count:
        logger.warning(
            "Persona-Generierung: %d von %d Personas erstellt",
            len(all_personas), persona_count,
        )
    elif len(all_personas) > persona_count:
        all_personas = all_personas[:persona_count]

    all_personas = _validate_and_adjust_personas(all_personas, persona_count)

    logger.info("Persona-Generierung abgeschlossen: %d Personas erstellt (Hybrid-Modus)", len(all_personas))
    return all_personas
