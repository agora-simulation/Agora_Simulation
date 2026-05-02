"""
Tick-Engine: Kern der Simulation (async).
Pro Tick (= 1 Ingame-Tag):
  1. Weltstand einlesen (selectinload — kein Lazy Loading)
  2. Feed pro Persona zusammenstellen (nur Posts der letzten 5 Tage)
  3. Personas in 3 Waves aufteilen (Mini-Batches innerhalb eines Ticks)
  4. Pro Wave: API-Calls parallel via asyncio.gather + Semaphore (max 10)
     → Posts/Kommentare/Reaktionen in DB schreiben (Multi-Action)
     → flush + Posts neu laden (damit nächste Wave die neuen Posts sieht)
  5. Sozialer Graph + Plattform-Affinität aktualisieren
  6. Ambient Mood berechnen + current_state jeder Persona aktualisieren (parallel)
  7. Influence Events aus State-Results extrahieren + DB speichern
  8. SimulationTick speichern + db.flush()
"""
import asyncio
import json
import logging
import random as _random
from uuid import UUID

logger = logging.getLogger("simulator.tick_engine")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.llm import LLMProvider, get_provider
from app.llm.resolver import ResolvedProvider
from app.models import (
    Persona,
    Post,
    Comment,
    Reaction,
    Simulation,
    SimulationTick,
    Platform,
    ReactionType,
    InfluenceEvent,
)

AGENT_SYSTEM_PROMPT = """Du bist eine virtuelle Person in einer sozialen Simulation.
Verhalte dich authentisch und konsistent mit deiner Persönlichkeit.
Reagiere auf deinen Feed wie eine echte Person — nicht immer, nicht immer positiv."""

STATE_SYSTEM_PROMPT = """Du analysierst die psychologische Entwicklung einer virtuellen Person.
Aktualisiere Meinungsentwicklung und Stimmung basierend auf den heutigen Aktionen."""


# ---------------------------------------------------------------------------
# Tool-Definitionen für Anthropic tool_use
# ---------------------------------------------------------------------------

PERSONA_ACTION_TOOL_NAME = "persona_action"
PERSONA_ACTION_TOOL_DESC = "Deine Aktion(en) für heute"
PERSONA_ACTION_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "description": "1-3 Aktionen die du heute durchführst",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["post", "comment", "react", "nothing"]},
                    "platform": {"type": "string", "enum": ["feedbook", "threadit"]},
                    "content": {"type": "string"},
                    "react_to_post_id": {"type": "string"},
                    "reaction_type": {"type": "string", "enum": ["like", "dislike", "share"]},
                    "comment_on_post_id": {"type": "string"},
                    "subreddit": {"type": "string"},
                },
                "required": ["action"],
            },
            "minItems": 1,
            "maxItems": 3,
        }
    },
    "required": ["actions"],
}

STATE_UPDATE_TOOL_NAME = "state_update"
STATE_UPDATE_TOOL_DESC = "Aktualisierter psychologischer Zustand der Persona"
STATE_UPDATE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "opinion_evolution": {
            "type": "string",
            "description": "Wie sich die Meinung entwickelt hat (1-2 Sätze)",
        },
        "mood": {
            "type": "string",
            "description": "Aktuelle Stimmung (ein Wort, z.B. begeistert, skeptisch, neugierig)",
        },
        "most_influential_post_id": {
            "type": "string",
            "description": "Post-ID aus dem Feed die deine Meinung heute am meisten beeinflusst hat (oder null wenn keiner)",
        },
        "memorable_event": {
            "type": "object",
            "description": "Erinnerungswürdiges Ereignis dieses Tages (falls vorhanden)",
            "properties": {
                "should_remember": {
                    "type": "boolean",
                    "description": "True wenn dieses Ereignis erinnerungswürdig war",
                },
                "type": {
                    "type": "string",
                    "enum": ["conflict", "persuasion", "social", "surprise", "personal"],
                    "description": "Art der Erinnerung",
                },
                "summary": {
                    "type": "string",
                    "description": "1-2 Sätze was passiert ist und warum es wichtig war",
                },
                "emotional_weight": {
                    "type": "number",
                    "description": "Emotionale Bedeutung 0.0-1.0",
                },
            },
        },
        "opinion_shifts": {
            "type": "object",
            "description": "Meinungsänderungen pro Dimension (Deltas -0.3 bis +0.3)",
            "properties": {
                "product_quality": {"type": "number"},
                "price_fairness": {"type": "number"},
                "brand_trust": {"type": "number"},
                "innovation": {"type": "number"},
                "ethical_concerns": {"type": "number"},
                "social_proof": {"type": "number"},
                "personal_relevance": {"type": "number"},
            },
        },
    },
    "required": ["opinion_evolution", "mood"],
}


# --- Memory-Management ---
MEMORY_MAX_ENTRIES = 30
MEMORY_DECAY_WEIGHT_THRESHOLD = 0.3
MEMORY_DECAY_AFTER_TICKS = 10

# --- Opinion Dimensions Defaults ---
OPINION_DIMENSIONS_KEYS = [
    "product_quality", "price_fairness", "brand_trust",
    "innovation", "ethical_concerns", "social_proof", "personal_relevance",
]


def _init_opinion_dimensions(is_skeptic: bool) -> dict:
    """Initialisiert die Meinungsdimensionen basierend auf Skeptiker-Status."""
    base = -0.2 if is_skeptic else 0.2
    import random
    return {
        key: max(-1.0, min(1.0, base + random.uniform(-0.2, 0.2)))
        for key in OPINION_DIMENSIONS_KEYS
    }


def _update_memory(
    persona_memory: list,
    new_event: dict | None,
    current_tick: int,
) -> list:
    """Aktualisiert die Persona-Memory.

    - Fügt neue Erinnerung hinzu (falls should_remember=True)
    - Lässt schwache Erinnerungen verfallen (weight < 0.3 nach 10 Ticks)
    - Hält Maximum von 30 Erinnerungen
    - Starke Erinnerungen (>= 0.7) verfallen nie
    """
    memories = list(persona_memory or [])

    # Vergessen: schwache Erinnerungen (weight < 0.3) verfallen nach 10 Ticks.
    # Mittlere (0.3-0.7) und starke (>= 0.7) Erinnerungen bleiben.
    memories = [
        m for m in memories
        if m.get("emotional_weight", 0) >= MEMORY_DECAY_WEIGHT_THRESHOLD
        or (current_tick - m.get("tick", 0)) <= MEMORY_DECAY_AFTER_TICKS
    ]

    # Neue Erinnerung hinzufügen
    if new_event and new_event.get("should_remember") and new_event.get("summary"):
        entry = {
            "tick": current_tick,
            "type": new_event.get("type", "personal"),
            "summary": new_event.get("summary", ""),
            "emotional_weight": float(new_event.get("emotional_weight", 0.5)),
        }
        memories.append(entry)

    # Maximum einhalten: niedrigstes emotional_weight entfernen
    if len(memories) > MEMORY_MAX_ENTRIES:
        memories.sort(key=lambda m: m.get("emotional_weight", 0), reverse=True)
        memories = memories[:MEMORY_MAX_ENTRIES]

    return memories


# ---------------------------------------------------------------------------
# Feed-Builder (sync — kein I/O)
# ---------------------------------------------------------------------------

def build_feed(
    persona: Persona,
    posts: list[Post],
    ingame_day: int,
    max_items: int = 10,
    all_personas: list | None = None,
) -> list[dict]:
    """Erstellt einen personalisierten Feed für eine Persona.

    Score = Verbindungen×3 + Kommentare×0.5 + Reaktionen
          + Recency-Decay + Trending-Bonus + Plattform-Affinität.
    Gibt die Top-max_items Posts als Dicts zurück.
    """
    connection_ids = set(str(c) for c in (persona.social_connections or []))

    # Plattform-Affinität aus current_state lesen
    platform_affinity = (persona.current_state or {}).get("platform_affinity", {})

    scored: list[tuple[float, Post]] = []
    for post in posts:
        score: float = 0.0
        if str(post.author_id) in connection_ids:
            score += 3
        score += len(post.comments) * 0.5
        score += len(post.reactions)

        # Recency-Decay: ältere Posts werden abgewertet
        score *= max(0.1, 1.0 - (ingame_day - post.ingame_day) * 0.15)

        # Trending-Bonus: Posts mit >5 Reaktionen bekommen +2 für alle
        if len(post.reactions) > 5:
            score += 2

        # Modul 5: Confirmation Bias Score (Echokammer-Mechanik)
        if all_personas is not None:
            persona_dims = (persona.current_state or {}).get("opinion_dimensions", {})
            if persona_dims:
                avg_opinion = sum(persona_dims.values()) / len(persona_dims)
                author = next(
                    (p for p in all_personas if str(p.id) == str(post.author_id)),
                    None,
                )
                if author:
                    author_dims = (author.current_state or {}).get("opinion_dimensions", {})
                    if author_dims:
                        author_avg = sum(author_dims.values()) / len(author_dims)
                        similarity = 1.0 - abs(avg_opinion - author_avg)
                        confirmation_bias = similarity * 2.0

                        # Offene Personas bekommen weniger Echokammer-Effekt
                        openness = (persona.personality_traits or {}).get("openness", 0.5)
                        if openness > 0.7:
                            confirmation_bias *= 0.7

                        score += confirmation_bias

        # Plattform-Affinität: 0.5-1.5x Multiplikator
        platform_bonus = platform_affinity.get(post.platform.value, 0.5)
        score *= (0.5 + platform_bonus)

        scored.append((score, post))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_posts = [p for _, p in scored[:max_items]]

    return [
        {
            "post_id": str(p.id),
            "author": p.author.name if p.author else "Unbekannt",
            "platform": p.platform.value,
            "content": p.content,
            "ingame_day": p.ingame_day,
            "comments_count": len(p.comments),
            "reactions_count": len(p.reactions),
        }
        for p in top_posts
    ]


# ---------------------------------------------------------------------------
# Persona-History Builder (sync — kein I/O)
# ---------------------------------------------------------------------------

def _get_persona_history(
    persona: Persona,
    posts: list[Post],
    max_own_posts: int = 5,
) -> str:
    """Sammelt die eigenen Posts der Persona + erhaltene Kommentare."""
    own_posts = [p for p in posts if str(p.author_id) == str(persona.id)]
    # Neueste zuerst, max 5
    own_posts.sort(key=lambda p: p.ingame_day, reverse=True)
    own_posts = own_posts[:max_own_posts]

    if not own_posts:
        return ""

    lines = ["=== Deine bisherigen Beiträge ==="]
    for post in own_posts:
        lines.append(f"[Tag {post.ingame_day}, {post.platform.value}] {post.content[:120]}")
        # Kommentare auf diesen Post
        if post.comments:
            for c in post.comments[:3]:  # Max 3 Kommentare pro Post
                author_name = c.author.name if c.author else "Jemand"
                lines.append(f"  \u2514 {author_name}: {c.content[:80]}")
        # Reaktionen
        if post.reactions:
            likes = sum(1 for r in post.reactions if r.reaction_type.value == "like")
            dislikes = sum(1 for r in post.reactions if r.reaction_type.value == "dislike")
            shares = sum(1 for r in post.reactions if r.reaction_type.value == "share")
            parts = []
            if likes:
                parts.append(f"{likes}x Like")
            if dislikes:
                parts.append(f"{dislikes}x Dislike")
            if shares:
                parts.append(f"{shares}x Share")
            if parts:
                lines.append(f"  Reaktionen: {', '.join(parts)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt-Builder (sync — kein I/O)
# ---------------------------------------------------------------------------

def _build_persona_profile_block(persona: Persona, compact: bool = False) -> str:
    """Baut den Persona-Profil-Text.

    compact=True: Kurzversion für Fast-Tier Calls (Tick-Actions, State-Updates).
    compact=False: Vollversion für Chat und Report.
    """
    state = persona.current_state or {}
    mood = state.get("mood", "neutral")

    # Basis-Profil (immer)
    ptype = getattr(persona, "persona_type", "individual") or "individual"
    if ptype == "individual":
        result = (
            f"Du bist {persona.name}, {persona.age}, {persona.location}, {persona.occupation}.\n"
        )
    elif ptype == "organization":
        subtype = getattr(persona, "entity_subtype", "") or "Unternehmen"
        result = (
            f"Du bist der offizielle Social-Media-Account von {persona.name} ({subtype}).\n"
            f"Standort: {persona.location}. Gegründet: {persona.age}.\n"
        )
    elif ptype == "institution":
        subtype = getattr(persona, "entity_subtype", "") or "Institution"
        result = (
            f"Du bist der offizielle Account von {persona.name} ({subtype}).\n"
            f"Standort: {persona.location}.\n"
        )
    elif ptype == "politician":
        subtype = getattr(persona, "entity_subtype", "") or "Politiker"
        result = (
            f"Du bist {persona.name}, {subtype}, {persona.location}.\n"
        )
    else:
        result = (
            f"Du bist {persona.name}, {persona.age}, {persona.location}, {persona.occupation}.\n"
        )

    result += (
        f"Persönlichkeit: {persona.personality}\n"
        f"Stil: {persona.communication_style}\n"
        f"Grundhaltung: {persona.initial_opinion}\n"
        f"Skeptiker: {'Ja' if persona.is_skeptic else 'Nein'}\n"
        f"Stimmung: {mood}"
    )

    # Big Five — nur die 2-3 stärksten Verhaltenshinweise
    traits = persona.personality_traits or {}
    if traits:
        hints = []
        if traits.get("extraversion", 0.5) > 0.7:
            hints.append("gesellig, postet oft")
        elif traits.get("extraversion", 0.5) < 0.3:
            hints.append("introvertiert, beobachtet mehr")
        if traits.get("agreeableness", 0.5) < 0.3:
            hints.append("direkt und kritisch")
        if traits.get("openness", 0.5) < 0.3:
            hints.append("skeptisch gegenüber Neuem")
        if hints:
            result += f"\nCharakter: {', '.join(hints)}"

    # Plattform-Präferenz (kurz)
    platform_affinity = state.get("platform_affinity", {})
    if platform_affinity:
        preferred = max(platform_affinity, key=platform_affinity.get)
        result += f"\nPlattform: {preferred}"

    if compact:
        # Kompakt: nur Meinungs-Zusammenfassung als Text, keine Details
        opinion_evolution = state.get("opinion_evolution", "")
        if opinion_evolution:
            result += f"\nMeinung: {opinion_evolution}"
        return result

    # --- Vollversion ab hier ---

    # Meinungsentwicklung
    opinion_evolution = state.get("opinion_evolution", persona.initial_opinion or "")
    recent_actions = state.get("recent_actions", [])
    if opinion_evolution:
        result += f"\n\nMeinungsentwicklung: {opinion_evolution}"
    if recent_actions:
        result += f"\nLetzte Aktionen: {json.dumps(recent_actions, ensure_ascii=False)}"

    # Modul 1: Langzeitgedächtnis — Top-5
    memories = list(persona.memory or [])
    if memories:
        memories_sorted = sorted(memories, key=lambda m: m.get("emotional_weight", 0), reverse=True)
        result += "\n\n=== Erinnerungen ==="
        for mem in memories_sorted[:5]:
            weight = mem.get("emotional_weight", 0)
            label = "!" if weight >= 0.7 else ("~" if weight >= 0.4 else ".")
            result += f"\n{label} [Tag {mem.get('tick', '?')}] {mem.get('summary', '')}"

    # Modul 2: Mehrdimensionale Meinung
    opinion_dims = state.get("opinion_dimensions", {})
    if opinion_dims:
        dims_short = []
        for key, val in opinion_dims.items():
            short_key = key.replace("_", " ").replace("product ", "").replace("personal ", "")
            if val >= 0.3:
                dims_short.append(f"{short_key}:+")
            elif val <= -0.3:
                dims_short.append(f"{short_key}:-")
        if dims_short:
            result += f"\n\nMeinungsprofil: {', '.join(dims_short)}"

    return result


# ---------------------------------------------------------------------------
# Dynamischer Sozialer Graph (Feature A)
# ---------------------------------------------------------------------------

def _update_social_graph(personas: list[Persona], posts: list[Post], ingame_day: int):
    """Aktualisiert social_connections basierend auf Interaktionen.

    Regeln:
    - Kommentar auf jemandes Post: +2.0 Verbindungsstärke
    - Reaktion (like/share) auf jemandes Post: +1.0
    - Reaktion (dislike) auf jemandes Post: -0.5
    - Alle Verbindungen decayen pro Tick um 5% (vergessen)
    - Top 3-8 stärkste Verbindungen werden social_connections
    """
    # Persona-ID-Map für schnellen Zugriff
    persona_map = {str(p.id): p for p in personas}

    # Posts dieses Ticks
    todays_posts = [p for p in posts if p.ingame_day == ingame_day]

    for persona in personas:
        state = dict(persona.current_state) if persona.current_state else {}
        strengths: dict[str, float] = dict(state.get("connection_strength", {}))

        # Decay: alle bestehenden Verbindungen um 5% abschwächen
        for pid in list(strengths.keys()):
            strengths[pid] *= 0.95
            if strengths[pid] < 0.1:
                del strengths[pid]  # Zu schwache Verbindungen entfernen

        state["connection_strength"] = strengths
        persona.current_state = state

    # Interaktionen dieses Ticks auswerten
    for post in todays_posts:
        author_id = str(post.author_id)

        # Kommentare auf diesen Post
        for comment in (post.comments or []):
            commenter_id = str(comment.author_id)
            if commenter_id != author_id and commenter_id in persona_map:
                # Commenter → Author: +2.0
                p = persona_map[commenter_id]
                state = dict(p.current_state) if p.current_state else {}
                strengths = dict(state.get("connection_strength", {}))
                strengths[author_id] = strengths.get(author_id, 0) + 2.0
                state["connection_strength"] = strengths
                p.current_state = state

        # Reaktionen auf diesen Post
        for reaction in (post.reactions or []):
            reactor_id = str(reaction.persona_id)
            if reactor_id != author_id and reactor_id in persona_map:
                p = persona_map[reactor_id]
                state = dict(p.current_state) if p.current_state else {}
                strengths = dict(state.get("connection_strength", {}))
                delta = -0.5 if reaction.reaction_type.value == "dislike" else 1.0
                strengths[author_id] = strengths.get(author_id, 0) + delta
                state["connection_strength"] = strengths
                p.current_state = state

    # Social Connections aktualisieren: Top 3-8 stärkste Verbindungen
    for persona in personas:
        state = dict(persona.current_state) if persona.current_state else {}
        strengths = state.get("connection_strength", {})

        if not strengths:
            continue

        # Sortiert nach Stärke, Top 3-8
        sorted_connections = sorted(strengths.items(), key=lambda x: x[1], reverse=True)
        n = min(max(3, len(sorted_connections)), 8)
        persona.social_connections = [pid for pid, _ in sorted_connections[:n]]


# ---------------------------------------------------------------------------
# Plattform-Migration (Feature D)
# ---------------------------------------------------------------------------

def _update_platform_affinity(personas: list[Persona], posts: list[Post], ingame_day: int):
    """Aktualisiert die Plattform-Präferenz basierend auf erhaltenem Engagement."""
    todays_posts = [p for p in posts if p.ingame_day == ingame_day]

    for persona in personas:
        state = dict(persona.current_state) if persona.current_state else {}
        affinity = dict(state.get("platform_affinity", {"feedbook": 0.5, "threadit": 0.5}))

        # Engagement auf eigenen Posts zählen
        own_posts = [p for p in todays_posts if str(p.author_id) == str(persona.id)]
        for post in own_posts:
            platform = post.platform.value
            engagement = len(post.comments or []) + len(post.reactions or [])
            # Positives Engagement stärkt die Plattform-Affinität
            if engagement > 0:
                affinity[platform] = affinity.get(platform, 0.5) + engagement * 0.05

        # Normalisieren (Summe = 1.0)
        total = sum(affinity.values())
        if total > 0:
            affinity = {k: v / total for k, v in affinity.items()}

        state["platform_affinity"] = affinity
        persona.current_state = state


# ---------------------------------------------------------------------------
# Emotionale Ansteckung (Feature B)
# ---------------------------------------------------------------------------

def _calculate_ambient_mood(persona: Persona, posts: list[Post]) -> str:
    """Berechnet die vorherrschende Stimmung im Feed einer Persona."""
    connection_ids = set(str(c) for c in (persona.social_connections or []))

    # Posts von Verbindungen sammeln
    connected_posts = [p for p in posts if str(p.author_id) in connection_ids]
    if not connected_posts:
        return "neutral"

    # Engagement-gewichtete Stimmungs-Indikatoren
    positive_signals = 0
    negative_signals = 0

    for post in connected_posts:
        likes = sum(1 for r in (post.reactions or []) if r.reaction_type.value == "like")
        shares = sum(1 for r in (post.reactions or []) if r.reaction_type.value == "share")
        dislikes = sum(1 for r in (post.reactions or []) if r.reaction_type.value == "dislike")

        positive_signals += likes + shares
        negative_signals += dislikes

        # Kommentare zählen als Engagement (neutral-positiv)
        positive_signals += len(post.comments or []) * 0.5

    total = positive_signals + negative_signals
    if total == 0:
        return "neutral"

    ratio = positive_signals / total
    if ratio > 0.7:
        return "überwiegend positiv"
    elif ratio < 0.3:
        return "überwiegend negativ"
    elif ratio < 0.5:
        return "eher kritisch"
    else:
        return "gemischt"


# ---------------------------------------------------------------------------
# Persona-Action (async — ein API-Call pro Persona, mit tool_use)
# ---------------------------------------------------------------------------

async def persona_action(
    persona: Persona,
    feed: list[dict],
    ingame_day: int,
    semaphore: asyncio.Semaphore,
    persona_history: str = "",
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> dict:
    """Lässt eine Persona auf ihren Feed reagieren.

    Gibt ein strukturiertes Dict mit {"actions": [...]} zurück.
    Bei jedem Fehler wird {"actions": [{"action": "nothing"}]} zurückgegeben,
    damit ein einzelner Fehler die gesamte Gather-Runde nicht abbricht.
    """
    feed_text = (
        json.dumps(feed, ensure_ascii=False, indent=2) if feed else "Noch keine Beiträge."
    )
    persona_profile = _build_persona_profile_block(persona, compact=True)
    history_block = f"{persona_history}\n\n" if persona_history else ""

    if provider is None:
        provider = get_provider(None)

    try:
        async with semaphore:
            return await provider.call_tool(
                tier="fast",
                system=AGENT_SYSTEM_PROMPT,
                cache_system=True,
                user_blocks=[
                    {"text": persona_profile, "cache": True},
                    {
                        "text": (
                            f"Ingame-Tag {ingame_day}.\n\n"
                            f"{history_block}"
                            f"=== Dein Feed heute ===\n{feed_text}\n\n"
                            f"Was tust du heute? Du kannst 1-3 Aktionen durchführen "
                            f"(posten, kommentieren, reagieren oder nichts tun). "
                            f"Nutze das persona_action Tool."
                        ),
                    },
                ],
                tool_name=PERSONA_ACTION_TOOL_NAME,
                tool_description=PERSONA_ACTION_TOOL_DESC,
                tool_schema=PERSONA_ACTION_TOOL_SCHEMA,
                max_tokens=3072,
                model=model,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
            )
    except Exception as e:
        logger.warning(f"persona_action für {persona.name} fehlgeschlagen: {e}")
        return {"actions": [{"action": "nothing"}]}


# ---------------------------------------------------------------------------
# State-Updater (async — Ringpuffer + Haiku-Call für mood/opinion_evolution)
# ---------------------------------------------------------------------------

def _derive_action_summary(action: dict) -> str:
    """Leitet eine lesbare Zusammenfassung aus einem Action-Dict ab."""
    action_type = action.get("action", "nothing")
    if action_type == "post":
        return f"Post verfasst: {action.get('content', '')[:80]}"
    if action_type == "comment":
        return f"Kommentar geschrieben: {action.get('content', '')[:80]}"
    if action_type == "react":
        return f"Reaktion ({action.get('reaction_type', '')}) auf Post"
    return "Keine Aktion"


async def update_persona_state_async(
    persona: Persona,
    action_summaries: list[str],
    tick_number: int,
    semaphore: asyncio.Semaphore,
    ambient_mood: str = "neutral",
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> tuple[dict, str | None]:
    """Aktualisiert den current_state einer Persona asynchron.

    1. Befüllt den Ringpuffer recent_actions (max 5).
    2. Setzt einen Mini-Haiku-Call ab, der opinion_evolution und mood aktualisiert.
    Bei Fehler im Haiku-Call bleiben opinion_evolution und mood unverändert.
    Gibt ein Tuple (neues current_state-Dict, most_influential_post_id oder None) zurück.
    """
    state = dict(persona.current_state) if persona.current_state else {}

    # --- 1. Ringpuffer recent_actions ---
    recent_actions: list[dict] = list(state.get("recent_actions", []))
    for summary in action_summaries:
        recent_actions.append(
            {
                "tick": tick_number,
                "summary": summary,
            }
        )
    if len(recent_actions) > 5:
        recent_actions = recent_actions[-5:]
    state["recent_actions"] = recent_actions

    # Sicherstellen, dass opinion_evolution und mood initialisiert sind
    if "opinion_evolution" not in state:
        state["opinion_evolution"] = persona.initial_opinion or ""
    if "mood" not in state:
        state["mood"] = "neutral"

    # --- 2. Mini-Haiku-Call für opinion_evolution + mood (via tool_use) ---
    current_opinion = state.get("opinion_evolution", "")
    current_mood = state.get("mood", "neutral")

    combined_summary = "; ".join(action_summaries) if action_summaries else "Keine Aktion"

    prompt = (
        f"Persona: {persona.name}, {persona.age}J, {persona.location}\n"
        f"Persönlichkeit: {persona.personality}\n"
        f"Bisherige Meinungsentwicklung: {current_opinion}\n"
        f"Aktuelle Stimmung: {current_mood}\n"
        f"Stimmung im sozialen Umfeld: {ambient_mood}\n"
        f"Heutige Aktionen (Tag {tick_number}): {combined_summary}\n\n"
        f"Beschreibe in 1-2 Sätzen wie sich die Meinung dieser Person entwickelt hat, "
        f"dann gib die aktuelle Stimmung als ein Wort an. "
        f"Welcher Post aus dem Feed hat die Meinung dieser Person heute am meisten beeinflusst? "
        f"Gib die post_id an (oder null wenn keiner entscheidend war). "
        f"Nutze das state_update Tool."
    )

    influential_post_id = None
    if provider is None:
        provider = get_provider(None)

    try:
        async with semaphore:
            parsed = await provider.call_tool(
                tier="fast",
                system=STATE_SYSTEM_PROMPT,
                cache_system=True,
                user_blocks=[{"text": prompt}],
                tool_name=STATE_UPDATE_TOOL_NAME,
                tool_description=STATE_UPDATE_TOOL_DESC,
                tool_schema=STATE_UPDATE_TOOL_SCHEMA,
                max_tokens=3072,
                model=model,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
            )

        if "opinion_evolution" in parsed:
            state["opinion_evolution"] = str(parsed["opinion_evolution"])
        if "mood" in parsed:
            state["mood"] = str(parsed["mood"])
        if "most_influential_post_id" in parsed:
            influential_post_id = parsed.get("most_influential_post_id")

        # Modul 1: Memory-Update
        memorable_event = parsed.get("memorable_event")
        if memorable_event:
            persona_memory = list(persona.memory or [])
            updated_memory = _update_memory(persona_memory, memorable_event, tick_number)
            persona.memory = updated_memory

        # Modul 2: Opinion Dimensions Update
        opinion_shifts = parsed.get("opinion_shifts", {})
        if opinion_shifts:
            dims = dict(state.get("opinion_dimensions", {}))
            # Initialisieren falls noch nicht vorhanden
            if not dims:
                dims = _init_opinion_dimensions(persona.is_skeptic or False)

            # Deltas anwenden (mit Big-Five-Offenheits-Multiplikator)
            traits = persona.personality_traits or {}
            openness = traits.get("openness", 0.5)
            openness_multiplier = 1.3 if openness > 0.7 else (0.7 if openness < 0.3 else 1.0)

            for key in OPINION_DIMENSIONS_KEYS:
                delta = float(opinion_shifts.get(key, 0.0))
                delta *= openness_multiplier
                current = dims.get(key, 0.0)
                dims[key] = max(-1.0, min(1.0, current + delta))

            state["opinion_dimensions"] = dims

    except Exception as e:
        # Bei Fehler: opinion_evolution und mood aus bestehendem state unverändert lassen
        logger.warning(f"State-Update für {persona.name} fehlgeschlagen: {e}")

    return state, influential_post_id


# ---------------------------------------------------------------------------
# Run Tick (async — Haupt-Orchestrator eines einzelnen Ticks)
# ---------------------------------------------------------------------------

async def run_tick(
    simulation_id: UUID,
    tick_number: int,
    ingame_day: int,
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
    provider: LLMProvider | None = None,
    action_resolved: ResolvedProvider | None = None,
    state_resolved: ResolvedProvider | None = None,
) -> SimulationTick:
    """Führt einen kompletten Tick aus.

    Lädt Personas und Posts (letzte 5 Tage) separat via selectinload.
    Teilt Personas in 3 Waves auf (30/30/40%) — jede Wave sieht die Posts
    der vorherigen Waves. Personas erhalten ihre eigenen bisherigen Posts
    + erhaltene Kommentare als Kontext im Prompt.
    Nach allen Waves: Sozialer Graph + Plattform-Affinität aktualisieren.
    Ambient Mood berechnen + State-Updates parallel via asyncio.gather.
    Influence Events aus State-Results extrahieren + in DB schreiben.
    Schreibt Ergebnisse in DB. Kein commit — der Runner macht den commit.
    """
    # --- Simulation + Personas laden (ohne Posts) ---
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.personas))
        .where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one()
    personas: list[Persona] = sim.personas

    # Provider-Auflösung: neues System (ResolvedProvider) oder Legacy
    if action_resolved:
        provider = action_resolved.provider
        fast_model_override = action_resolved.model
        action_temperature = action_resolved.temperature
        action_top_p = action_resolved.top_p
        action_top_k = action_resolved.top_k
    elif provider is None:
        provider = get_provider(getattr(sim, "llm_provider", None))
        fast_model_override = getattr(sim, "llm_model_fast", None) or None
        action_temperature = None
        action_top_p = None
        action_top_k = None
    else:
        fast_model_override = getattr(sim, "llm_model_fast", None) or None
        action_temperature = None
        action_top_p = None
        action_top_k = None

    # State-Update Provider (kann ein anderer sein)
    if state_resolved:
        state_provider = state_resolved.provider
        state_model = state_resolved.model
        state_temperature = state_resolved.temperature
        state_top_p = state_resolved.top_p
        state_top_k = state_resolved.top_k
    else:
        state_provider = provider
        state_model = fast_model_override
        state_temperature = action_temperature
        state_top_p = action_top_p
        state_top_k = action_top_k

    # --- Posts separat laden: nur letzte 5 Ingame-Tage ---
    min_day = max(1, ingame_day - 5)
    posts_result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.comments).selectinload(Comment.author),
            selectinload(Post.reactions),
            selectinload(Post.author),
        )
        .where(Post.simulation_id == simulation_id)
        .where(Post.ingame_day >= min_day)
    )
    existing_posts: list[Post] = list(posts_result.scalars().all())

    logger.debug(
        f"Tick {tick_number}: {len(personas)} Personas, "
        f"{len(existing_posts)} Posts (Tage {min_day}-{ingame_day})"
    )

    # --- Personas in 3 Waves aufteilen (30/30/40%) ---
    shuffled = list(personas)
    _random.shuffle(shuffled)
    n = len(shuffled)
    cut1 = max(1, n * 30 // 100)
    cut2 = max(cut1 + 1, n * 60 // 100)
    waves = [shuffled[:cut1], shuffled[cut1:cut2], shuffled[cut2:]]

    # Mutable Post-Liste + Valid-IDs
    all_posts = list(existing_posts)
    valid_post_ids = {str(p.id) for p in all_posts}

    # Tracking über alle Waves
    new_posts_count = 0
    new_comments_count = 0
    new_reactions_count = 0
    total_active = 0
    all_persona_summaries: dict[str, list[str]] = {}
    # persona_id → [(post_id, influence_type), ...]  für deterministische Influence-Events
    persona_interactions: dict[str, list[tuple[str, str]]] = {}

    for wave_num, wave_personas in enumerate(waves, 1):
        if not wave_personas:
            continue

        logger.debug(
            f"Tick {tick_number} Wave {wave_num}: {len(wave_personas)} Personas"
        )

        # --- Feeds bauen mit aktuellem Post-Stand ---
        feeds = {
            str(p.id): build_feed(p, all_posts, ingame_day, all_personas=personas)
            for p in wave_personas
        }

        # --- Persona-History bauen (eigene Posts + erhaltene Kommentare) ---
        histories = {
            str(p.id): _get_persona_history(p, all_posts)
            for p in wave_personas
        }

        # --- Persona-Calls parallel (max 10 concurrent via Semaphore) ---
        results = await asyncio.gather(
            *[
                persona_action(
                    p,
                    feeds[str(p.id)],
                    ingame_day,
                    semaphore,
                    histories[str(p.id)],
                    provider=provider,
                    model=fast_model_override,
                    temperature=action_temperature,
                    top_p=action_top_p,
                    top_k=action_top_k,
                )
                for p in wave_personas
            ],
            return_exceptions=True,
        )

        # --- Ergebnisse verarbeiten: Multi-Action + DB-Writes ---
        for persona, action_result in zip(wave_personas, results):
            if isinstance(action_result, Exception):
                action_result = {"actions": [{"action": "nothing"}]}

            actions_list = action_result.get("actions", [{"action": "nothing"}])
            if not actions_list:
                actions_list = [{"action": "nothing"}]

            # Defensiv: Modell liefert manchmal Strings statt Dicts — filtern.
            actions_list = [a for a in actions_list if isinstance(a, dict)]
            if not actions_list:
                actions_list = [{"action": "nothing"}]

            summaries: list[str] = []
            persona_was_active = False

            for action in actions_list:
                action_type: str = action.get("action", "nothing")
                action_summary: str = ""

                if action_type == "post" and action.get("content"):
                    platform_val = action.get("platform", "feedbook")
                    try:
                        platform = Platform(platform_val)
                    except ValueError:
                        platform = Platform.feedbook

                    post = Post(
                        simulation_id=simulation_id,
                        author_id=persona.id,
                        platform=platform,
                        content=action["content"],
                        ingame_day=ingame_day,
                        subreddit=action.get("subreddit"),
                    )
                    db.add(post)
                    new_posts_count += 1
                    action_summary = f"Post auf {platform.value}: {action['content'][:60]}"
                    persona_was_active = True

                elif action_type == "react" and action.get("react_to_post_id"):
                    # Post-ID-Validierung
                    if action["react_to_post_id"] not in valid_post_ids:
                        logger.debug(
                            f"Persona {persona.name}: react auf ungültige Post-ID "
                            f"{action['react_to_post_id'][:8]} — übersprungen"
                        )
                        action_type = "nothing"
                    else:
                        try:
                            reaction_type = ReactionType(action.get("reaction_type", "like"))
                            reaction = Reaction(
                                post_id=UUID(action["react_to_post_id"]),
                                persona_id=persona.id,
                                reaction_type=reaction_type,
                                ingame_day=ingame_day,
                            )
                            db.add(reaction)
                            new_reactions_count += 1
                            action_summary = (
                                f"Reaktion {reaction_type.value} auf Post "
                                f"{action['react_to_post_id'][:8]}"
                            )
                            persona_was_active = True
                            # Influence tracken: Reaktion = Post hat Aufmerksamkeit ausgelöst
                            influence_type = (
                                "negative_reaction" if reaction_type.value == "dislike"
                                else "positive_reaction"
                            )
                            persona_interactions.setdefault(str(persona.id), []).append(
                                (action["react_to_post_id"], influence_type)
                            )
                        except Exception:
                            action_type = "nothing"

                elif (
                    action_type == "comment"
                    and action.get("comment_on_post_id")
                    and action.get("content")
                ):
                    # Post-ID-Validierung
                    if action["comment_on_post_id"] not in valid_post_ids:
                        logger.debug(
                            f"Persona {persona.name}: comment auf ungültige Post-ID "
                            f"{action['comment_on_post_id'][:8]} — übersprungen"
                        )
                        action_type = "nothing"
                    else:
                        try:
                            comment = Comment(
                                post_id=UUID(action["comment_on_post_id"]),
                                author_id=persona.id,
                                content=action["content"],
                                ingame_day=ingame_day,
                            )
                            db.add(comment)
                            new_comments_count += 1
                            action_summary = (
                                f"Kommentar auf Post {action['comment_on_post_id'][:8]}: "
                                f"{action['content'][:60]}"
                            )
                            persona_was_active = True
                            # Influence tracken: Kommentar = starke Auseinandersetzung mit Post
                            persona_interactions.setdefault(str(persona.id), []).append(
                                (action["comment_on_post_id"], "engagement")
                            )
                        except Exception:
                            action_type = "nothing"

                # action_summary ableiten falls leer (nothing-Fall)
                if not action_summary:
                    action_summary = _derive_action_summary(action)

                summaries.append(action_summary)

            if persona_was_active:
                total_active += 1

            all_persona_summaries[str(persona.id)] = summaries

        # --- Nach jeder Wave (außer der letzten): flush + Posts neu laden ---
        await db.flush()
        if wave_num < 3:
            posts_result = await db.execute(
                select(Post)
                .options(
                    selectinload(Post.comments).selectinload(Comment.author),
                    selectinload(Post.reactions),
                    selectinload(Post.author),
                )
                .where(Post.simulation_id == simulation_id)
                .where(Post.ingame_day >= min_day)
            )
            all_posts = list(posts_result.scalars().all())
            valid_post_ids = {str(p.id) for p in all_posts}

    logger.debug(
        f"Tick {tick_number}: {new_posts_count} Posts, "
        f"{new_comments_count} Kommentare, {new_reactions_count} Reaktionen erstellt"
    )

    # --- Posts nach letzter Wave neu laden (aktuellster Stand für Graph/Affinität) ---
    posts_result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.comments).selectinload(Comment.author),
            selectinload(Post.reactions),
            selectinload(Post.author),
        )
        .where(Post.simulation_id == simulation_id)
        .where(Post.ingame_day >= min_day)
    )
    all_posts = list(posts_result.scalars().all())
    valid_post_ids = {str(p.id) for p in all_posts}

    # --- 1. Sozialer Graph aktualisieren (Feature A) ---
    _update_social_graph(personas, all_posts, ingame_day)

    # --- 2. Plattform-Affinität aktualisieren (Feature D) ---
    _update_platform_affinity(personas, all_posts, ingame_day)

    # --- 3. Ambient Moods berechnen (Feature B) ---
    ambient_moods = {
        str(p.id): _calculate_ambient_mood(p, all_posts)
        for p in personas
    }

    # --- 4. State-Updates PARALLEL via asyncio.gather (mit ambient_mood) ---
    state_update_tasks = [
        update_persona_state_async(
            persona,
            all_persona_summaries.get(str(persona.id), ["Keine Aktion"]),
            tick_number,
            semaphore,
            ambient_mood=ambient_moods.get(str(persona.id), "neutral"),
            provider=state_provider,
            model=state_model,
            temperature=state_temperature,
            top_p=state_top_p,
            top_k=state_top_k,
        )
        for persona in personas
    ]
    state_results = await asyncio.gather(*state_update_tasks, return_exceptions=True)

    # --- 5. State-Results verarbeiten + Influence Events (Feature C) ---
    post_map = {str(p.id): p for p in all_posts}

    for persona, state_result in zip(personas, state_results):
        if isinstance(state_result, Exception):
            logger.warning(
                f"State-Update für {persona.name} fehlgeschlagen (Exception): {state_result}"
            )
        else:
            new_state, influential_post_id = state_result
            persona.current_state = new_state

            # Influence Events aus LLM-identifiziertem opinion_shift
            if influential_post_id and influential_post_id in valid_post_ids:
                source_post = post_map.get(influential_post_id)
                if source_post and str(source_post.author_id) != str(persona.id):
                    db.add(InfluenceEvent(
                        simulation_id=simulation_id,
                        source_persona_id=source_post.author_id,
                        target_persona_id=persona.id,
                        trigger_post_id=UUID(influential_post_id),
                        ingame_day=ingame_day,
                        influence_type="opinion_shift",
                        description=(
                            f"{persona.name} wurde von "
                            f"{source_post.author.name if source_post.author else 'Unbekannt'}"
                            f"'s Post in ihrer Meinung beeinflusst"
                        ),
                    ))

        # Deterministische Influence Events aus tatsächlichen Interaktionen
        for post_id, inf_type in persona_interactions.get(str(persona.id), []):
            source_post = post_map.get(post_id)
            if not source_post or str(source_post.author_id) == str(persona.id):
                continue
            author_name = source_post.author.name if source_post.author else "Unbekannt"
            if inf_type == "engagement":
                description = f"{persona.name} hat auf {author_name}s Post geantwortet"
            elif inf_type == "positive_reaction":
                description = f"{persona.name} hat auf {author_name}s Post positiv reagiert"
            else:
                description = f"{persona.name} hat {author_name}s Post abgelehnt"
            db.add(InfluenceEvent(
                simulation_id=simulation_id,
                source_persona_id=source_post.author_id,
                target_persona_id=persona.id,
                trigger_post_id=UUID(post_id),
                ingame_day=ingame_day,
                influence_type=inf_type,
                description=description,
            ))

    # --- 6. Tick-Snapshot speichern ---

    # Modul 5: Polarisierungs-Index berechnen
    import statistics
    persona_avg_opinions = []
    for p in personas:
        dims = (p.current_state or {}).get("opinion_dimensions", {})
        if dims:
            avg = sum(dims.values()) / len(dims)
            persona_avg_opinions.append(avg)

    polarization_index = 0.0
    echo_clusters = []
    if len(persona_avg_opinions) >= 2:
        polarization_index = round(statistics.stdev(persona_avg_opinions), 3)
        # Einfache Cluster-Bildung: positiv vs negativ
        pos_cluster = [str(p.id) for p in personas
                       if (p.current_state or {}).get("opinion_dimensions")
                       and sum((p.current_state or {}).get("opinion_dimensions", {}).values()) / 7 > 0.1]
        neg_cluster = [str(p.id) for p in personas
                       if (p.current_state or {}).get("opinion_dimensions")
                       and sum((p.current_state or {}).get("opinion_dimensions", {}).values()) / 7 <= 0.1]
        if pos_cluster:
            echo_clusters.append({"personas": pos_cluster, "avg_opinion": round(
                sum(sum((p.current_state or {}).get("opinion_dimensions", {}).values()) / 7
                    for p in personas if str(p.id) in pos_cluster) / len(pos_cluster), 2
            )})
        if neg_cluster:
            echo_clusters.append({"personas": neg_cluster, "avg_opinion": round(
                sum(sum((p.current_state or {}).get("opinion_dimensions", {}).values()) / 7
                    for p in personas if str(p.id) in neg_cluster) / len(neg_cluster), 2
            )})

    tick = SimulationTick(
        simulation_id=simulation_id,
        tick_number=tick_number,
        ingame_day=ingame_day,
        snapshot={
            "new_posts": new_posts_count,
            "new_comments": new_comments_count,
            "new_reactions": new_reactions_count,
            "personas_active": total_active,
            "polarization_index": polarization_index,
            "echo_chamber_clusters": echo_clusters,
        },
    )
    db.add(tick)

    await db.flush()

    return tick
