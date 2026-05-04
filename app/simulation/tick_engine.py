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

logger = logging.getLogger("agora.tick_engine")

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

# ---------------------------------------------------------------------------
# v1.1: Actor-Type Behavior Parameters
# ---------------------------------------------------------------------------

ACTOR_BEHAVIOR = {
    "private_person":     {"posts_per_tick": 0.3, "latency_min": 0, "latency_max": 1, "reach_mult": 1.0, "credibility": 0.5, "dropout_rate": 0.3, "decay_rate": 0.1},
    "company":            {"posts_per_tick": 0.1, "latency_min": 1, "latency_max": 3, "reach_mult": 12.0, "credibility": 0.6, "dropout_rate": 0.1, "decay_rate": 0.05},
    "research_institute": {"posts_per_tick": 0.05, "latency_min": 5, "latency_max": 10, "reach_mult": 20.0, "credibility": 0.9, "dropout_rate": 0.05, "decay_rate": 0.03},
    "authority":          {"posts_per_tick": 0.02, "latency_min": 7, "latency_max": 15, "reach_mult": 65.0, "credibility": 0.85, "dropout_rate": 0.05, "decay_rate": 0.02},
    "media":              {"posts_per_tick": 0.4, "latency_min": 1, "latency_max": 4, "reach_mult": 250.0, "credibility": 0.7, "dropout_rate": 0.05, "decay_rate": 0.08},
    "influencer":         {"posts_per_tick": 0.6, "latency_min": 0, "latency_max": 2, "reach_mult": 500.0, "credibility": 0.6, "dropout_rate": 0.05, "decay_rate": 0.1},
    "expert":             {"posts_per_tick": 0.2, "latency_min": 2, "latency_max": 5, "reach_mult": 25.0, "credibility": 0.85, "dropout_rate": 0.1, "decay_rate": 0.05},
    "collective":         {"posts_per_tick": 0.15, "latency_min": 3, "latency_max": 7, "reach_mult": 100.0, "credibility": 0.6, "dropout_rate": 0.08, "decay_rate": 0.04},
    "validator":          {"posts_per_tick": 0.01, "latency_min": 10, "latency_max": 20, "reach_mult": 65.0, "credibility": 0.95, "dropout_rate": 0.02, "decay_rate": 0.01},
}


def _should_persona_act(persona, ingame_day: int) -> bool:
    """v1.1: Determines if a persona should act this tick based on actor type behavior."""
    actor_type = getattr(persona, 'actor_type', 'private_person') or 'private_person'
    behavior = ACTOR_BEHAVIOR.get(actor_type, ACTOR_BEHAVIOR["private_person"])
    latency = getattr(persona, 'activation_latency', 0) or 0
    if ingame_day < latency:
        return False
    post_probability = behavior["posts_per_tick"]
    days_since_activation = ingame_day - latency
    if days_since_activation <= 3:
        post_probability *= 1.5
    decay_rate = getattr(persona, 'engagement_decay_rate', behavior["decay_rate"]) or behavior["decay_rate"]
    if days_since_activation > 5:
        post_probability *= max(0.1, 1.0 - decay_rate * (days_since_activation - 5))
    if _random.random() < behavior["dropout_rate"] and ingame_day > latency + 3:
        return False
    return _random.random() < post_probability


def _get_tonality_hint(persona) -> str:
    """v1.1: Returns a tonality hint based on actor type."""
    actor_type = getattr(persona, 'actor_type', 'private_person') or 'private_person'
    hints = {
        "private_person": "Sprich aus persoenlicher Erfahrung, emotional und direkt.",
        "company": "Formuliere offiziell, vorsichtig und markenkonform.",
        "research_institute": "Argumentiere evidenzbasiert und zurueckhaltend.",
        "authority": "Formuliere formal und regelorientiert.",
        "media": "Berichte neutral-skeptisch und story-orientiert.",
        "influencer": "Sprich persoenlich und polarisierend.",
        "expert": "Argumentiere sachlich und fachterminologisch.",
        "collective": "Vertritt das Gruppeninteresse. Mobilisiere.",
        "validator": "Formuliere formal-technisch. Gib Freigabe oder Ablehnung.",
    }
    return hints.get(actor_type, hints["private_person"])


async def _process_trigger_events(simulation_id: UUID, ingame_day: int, db) -> list[dict]:
    """v1.1: Processes trigger events scheduled for this day."""
    from app.models.trigger_event import TriggerEvent
    result = await db.execute(
        select(TriggerEvent).where(TriggerEvent.simulation_id == simulation_id, TriggerEvent.tick_day == ingame_day)
    )
    return [{"id": str(e.id), "event_type": e.event_type, "title": e.title, "content": e.content,
             "affected_segments": e.affected_segments or [], "intensity": e.intensity or "minor"}
            for e in result.scalars().all()]


def _detect_stagnation(tick_snapshots: list[dict], window: int = 3) -> bool:
    """v1.1: Detects stagnation based on rolling averages."""
    if len(tick_snapshots) < window:
        return False
    recent = tick_snapshots[-window:]
    avg_posts = sum(s.get("new_posts", 0) for s in recent) / window
    avg_active = sum(s.get("personas_active", 0) for s in recent) / window
    vals = [s.get("polarization_index", 0) for s in recent]
    import statistics as _stats
    sentiment_var = _stats.variance(vals) if len(vals) >= 2 else 0.0
    is_stagnant = avg_posts < 2 and sentiment_var < 0.05 and avg_active < 3
    if is_stagnant:
        logger.warning(f"Stagnation erkannt: posts={avg_posts:.1f}, var={sentiment_var:.4f}, active={avg_active:.1f}")
    return is_stagnant


async def _auto_reactivate(simulation_id, ingame_day, db, personas, mode="mild") -> list[str]:
    """v1.1: Auto-reactivates dormant personas."""
    if mode == "off":
        return []
    reactivations = []
    priority_order = ["media", "influencer", "authority", "validator", "expert", "collective", "company"]
    dormant = []
    for p in personas:
        at = getattr(p, 'actor_type', 'private_person') or 'private_person'
        recent = (p.current_state or {}).get("recent_actions", [])
        is_dormant = not any(a.get("tick", 0) >= ingame_day - 3 for a in recent)
        if is_dormant and at in priority_order:
            dormant.append((priority_order.index(at), p))
    dormant.sort(key=lambda x: x[0])
    for _, p in dormant[:2 if mode == "mild" else 5]:
        state = dict(p.current_state or {})
        state["mood"] = "aktiviert"
        p.current_state = state
        at = getattr(p, 'actor_type', 'private_person') or 'private_person'
        reactivations.append(f"Auto-Reactivation: {p.name} ({at})")
    if mode == "aggressive" and reactivations:
        from app.models.trigger_event import TriggerEvent
        db.add(TriggerEvent(simulation_id=simulation_id, tick_day=ingame_day, event_type="news_headline",
                            title=f"Neue Marktentwicklung (Tag {ingame_day})", content="Auto-generiert wegen Stagnation.",
                            affected_segments=["media", "influencer", "company"], intensity="minor",
                            source_attribution="System (Stagnations-Detection)", was_auto_generated=True))
        reactivations.append("Auto-Trigger-Event generiert")
    return reactivations


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT_BASE = """Du bist eine virtuelle Person in einer sozialen Simulation.
Verhalte dich authentisch und konsistent mit deiner Persönlichkeit.
Reagiere auf deinen Feed wie eine echte Person — nicht immer, nicht immer positiv.

WICHTIG: Erfinde KEINE konkreten Zahlen, Prozentsätze oder Statistiken (z.B. "+23% CTR", "-18% CAC", "ROI von 340%").
Du darfst nur qualitative Aussagen treffen ("deutlich bessere Ergebnisse", "spürbare Verbesserung", "merklicher Rückgang").
Wenn du Zahlen nennst, müssen sie direkt aus deinem Profil oder deiner Erfahrung stammen.
Erfundene Metriken verfälschen den Diskurs.

AKTEURS-TYPEN im Diskurs: Privatpersonen, Firmen, Institute, Behörden, Medien, Influencer, Experten, Kollektive, Validierer.
Reagiere angemessen auf Posts verschiedener Akteurs-Typen. Ein Behörden-Statement hat mehr Gewicht als ein anonymer Post."""

# Legacy-Kompatibilität
AGENT_SYSTEM_PROMPT = AGENT_SYSTEM_PROMPT_BASE


def _build_agent_system_prompt(market_context_summary: str | None = None) -> str:
    """Baut den Agent-System-Prompt, optional mit MarketContext."""
    prompt = AGENT_SYSTEM_PROMPT_BASE

    # v1.1: Add actor type context
    prompt += """

AKTEURS-TYPEN im Diskurs:
- Privatpersonen (emotional, persönlich), Firmen (offiziell, vorsichtig), Institute (evidenzbasiert),
  Behörden (formal), Medien (neutral-skeptisch), Influencer (persönlich, polarisierend),
  Experten (sachlich), Kollektive Akteure (mobilisierend), Validierer (formal-technisch, binäre Signale).
Reagiere angemessen auf Posts verschiedener Akteurs-Typen. Ein Behörden-Statement hat mehr Gewicht als ein anonymer Post."""

    if market_context_summary:
        prompt += f"""

=== AKTUELLE MARKTLAGE ===
{market_context_summary}
=== ENDE MARKTLAGE ===

Berücksichtige diese aktuelle Marktlage in deinem Verhalten und deinen Meinungen.
Deine Reaktionen sollten die reale Stimmung und die aktuellen Debatten widerspiegeln."""
    return prompt

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
    - Core Memories (type=persuasion oder weight >= 0.8) verfallen nie
    - Lässt schwache Erinnerungen verfallen (weight < 0.3 nach 10 Ticks)
    - Hält Maximum von 30 Erinnerungen
    - Starke Erinnerungen (>= 0.7) verfallen nie
    - Periodische Kompression: alle 5 Ticks werden schwache Memories zusammengefasst
    """
    memories = list(persona_memory or [])

    # Core Memories: Meinungsänderungen (persuasion) und stark emotionale (>=0.8) verfallen nie
    def _is_core_memory(m: dict) -> bool:
        return (
            m.get("type") == "persuasion"
            or m.get("emotional_weight", 0) >= 0.8
            or m.get("is_core", False)
        )

    # Vergessen: schwache Erinnerungen verfallen nach 10 Ticks (außer Core Memories)
    memories = [
        m for m in memories
        if _is_core_memory(m)
        or m.get("emotional_weight", 0) >= MEMORY_DECAY_WEIGHT_THRESHOLD
        or (current_tick - m.get("tick", 0)) <= MEMORY_DECAY_AFTER_TICKS
    ]

    # Periodische Kompression: alle 5 Ticks mittlere Memories zusammenfassen
    if current_tick > 0 and current_tick % 5 == 0:
        # Finde nicht-Core Memories mit weight 0.3-0.6
        compressible = [
            m for m in memories
            if not _is_core_memory(m)
            and 0.3 <= m.get("emotional_weight", 0) < 0.6
        ]
        if len(compressible) >= 3:
            # Zusammenfassen zu einer komprimierten Erinnerung
            summaries = [m.get("summary", "") for m in compressible[:5]]
            compressed = {
                "tick": current_tick,
                "type": "compressed",
                "summary": f"Zusammenfassung vergangener Eindrücke: {'; '.join(s[:50] for s in summaries)}",
                "emotional_weight": 0.5,
            }
            # Komprimierte ersetzen
            memories = [m for m in memories if m not in compressible[:5]]
            memories.append(compressed)

    # Neue Erinnerung hinzufügen
    if new_event and new_event.get("should_remember") and new_event.get("summary"):
        is_core = new_event.get("type") == "persuasion" or float(new_event.get("emotional_weight", 0.5)) >= 0.8
        entry = {
            "tick": current_tick,
            "type": new_event.get("type", "personal"),
            "summary": new_event.get("summary", ""),
            "emotional_weight": float(new_event.get("emotional_weight", 0.5)),
            "is_core": is_core,
        }
        memories.append(entry)

    # Maximum einhalten: niedrigstes emotional_weight entfernen (aber nie Core Memories)
    if len(memories) > MEMORY_MAX_ENTRIES:
        core = [m for m in memories if _is_core_memory(m)]
        non_core = [m for m in memories if not _is_core_memory(m)]
        non_core.sort(key=lambda m: m.get("emotional_weight", 0), reverse=True)
        max_non_core = MEMORY_MAX_ENTRIES - len(core)
        memories = core + non_core[:max(0, max_non_core)]

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
    polarization_index: float = 1.0,
) -> list[dict]:
    """Erstellt einen personalisierten Feed für eine Persona.

    Score = Verbindungen×3 + Kommentare×0.5 + Reaktionen
          + Recency-Decay + Trending-Bonus + Plattform-Affinität.

    Anti-Echo-Chamber-Mechaniken:
    - Confirmation Bias auf 0.5 reduziert (war 2.0)
    - Opposing-View-Injection: min. 2 Slots für Gegenmeinungen reserviert
    - Konsens-Bremse: bei Polarization < 0.15 werden kontroverse Posts bevorzugt
    """
    connection_ids = set(str(c) for c in (persona.social_connections or []))

    # Plattform-Affinität aus current_state lesen
    platform_affinity = (persona.current_state or {}).get("platform_affinity", {})

    # Persona-Durchschnittsmeinung für Bias-Berechnung
    persona_dims = (persona.current_state or {}).get("opinion_dimensions", {})
    persona_avg = (sum(persona_dims.values()) / len(persona_dims)) if persona_dims else 0.0

    scored: list[tuple[float, Post, float]] = []  # (score, post, opinion_distance)
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

        # Meinungsdistanz berechnen (für Opposing-View-Injection)
        opinion_distance = 0.0

        # Confirmation Bias — reduziert von 2.0 auf 0.5
        if all_personas is not None and persona_dims:
            author = next(
                (p for p in all_personas if str(p.id) == str(post.author_id)),
                None,
            )
            if author:
                author_dims = (author.current_state or {}).get("opinion_dimensions", {})
                if author_dims:
                    author_avg = sum(author_dims.values()) / len(author_dims)
                    opinion_distance = abs(persona_avg - author_avg)
                    similarity = 1.0 - opinion_distance
                    confirmation_bias = similarity * 0.5  # War: 2.0

                    # Offene Personas bekommen weniger Echokammer-Effekt
                    openness = (persona.personality_traits or {}).get("openness", 0.5)
                    if openness > 0.7:
                        confirmation_bias *= 0.7

                    score += confirmation_bias

                    # Konsens-Bremse: bei niedriger Polarisierung kontroverse Posts boosten
                    if polarization_index < 0.15 and opinion_distance > 0.3:
                        score += 2.0  # Kontroverse Stimmen im Konsens-Zustand sichtbarer machen

        # Plattform-Affinität: 0.5-1.5x Multiplikator
        platform_bonus = platform_affinity.get(post.platform.value, 0.5)
        score *= (0.5 + platform_bonus)

        scored.append((score, post, opinion_distance))

    scored.sort(key=lambda x: x[0], reverse=True)

    # --- Opposing-View-Injection ---
    # Reserviere min. 2 Slots für Posts mit hoher Meinungsdistanz (> 0.3)
    OPPOSING_SLOTS = 2
    top_posts = [p for _, p, _ in scored[:max_items]]

    # Finde Posts mit hoher Distanz die NICHT schon in top_posts sind
    top_post_ids = {str(p.id) for p in top_posts}
    opposing_candidates = [
        (score, post, dist) for score, post, dist in scored
        if dist > 0.3 and str(post.id) not in top_post_ids
    ]
    # Sortiere Opposing nach Distanz (höchste zuerst) und dann nach Score
    opposing_candidates.sort(key=lambda x: (-x[2], -x[0]))

    # Ersetze die schwächsten Posts im Feed durch Opposing-Views
    for i, (_, opp_post, _) in enumerate(opposing_candidates[:OPPOSING_SLOTS]):
        if len(top_posts) >= max_items:
            # Ersetze den schwächsten Post (letzten)
            top_posts[-1 - i] = opp_post
        else:
            top_posts.append(opp_post)

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

    # v1.1: Actor type system (backwards compatible)
    actor_type = getattr(persona, 'actor_type', None)
    ptype = getattr(persona, "persona_type", "individual") or "individual"

    # Use actor_type if available, fallback to legacy persona_type
    if actor_type and actor_type != "private_person":
        effective_type = actor_type
    elif ptype == "organization":
        effective_type = "company"
    elif ptype == "institution":
        effective_type = "collective"
    elif ptype == "politician":
        effective_type = "private_person"
    else:
        effective_type = actor_type or "private_person"

    stance = getattr(persona, 'stance', '') or ''
    stance_text = f" | Haltung: {stance}" if stance else ""
    context = getattr(persona, 'context', '') or ''
    context_text = f" | Kontext: {context}" if context else ""
    traegerschaft = getattr(persona, 'traegerschaft', '') or ''
    traeg_text = f" | Trägerschaft: {traegerschaft}" if traegerschaft else ""
    function_tags = getattr(persona, 'function_tags', []) or []
    tags_text = f" | Rollen: {', '.join(function_tags)}" if function_tags else ""

    if effective_type == "private_person":
        result = f"Du bist {persona.name}, {persona.age}, {persona.location}, {persona.occupation}.{context_text}{stance_text}\n"
    elif effective_type == "company":
        subtype = getattr(persona, "entity_subtype", "") or getattr(persona, "subtype", "") or "Unternehmen"
        result = f"Du bist der offizielle Social-Media-Account von {persona.name} ({subtype}).{traeg_text}{stance_text}\nStandort: {persona.location}.\n"
    elif effective_type == "research_institute":
        result = f"Du bist der offizielle Account von {persona.name} (Forschungsinstitut).{traeg_text}{stance_text}\nStandort: {persona.location}.\n"
    elif effective_type == "authority":
        result = f"Du bist der offizielle Account von {persona.name} (Behörde/Regulator).{stance_text}\nStandort: {persona.location}.\n"
    elif effective_type == "media":
        result = f"Du bist {persona.name} (Medium/Journalist).{traeg_text}{stance_text}\nStandort: {persona.location}.\n"
    elif effective_type == "influencer":
        result = f"Du bist {persona.name} (Influencer).{context_text}{stance_text}\n"
    elif effective_type == "expert":
        result = f"Du bist {persona.name}, Experte/Fachperson für {persona.occupation}.{stance_text}\nStandort: {persona.location}.\n"
    elif effective_type == "collective":
        subtype = getattr(persona, "entity_subtype", "") or getattr(persona, "subtype", "") or "Kollektiver Akteur"
        result = f"Du bist der offizielle Account von {persona.name} ({subtype}).{traeg_text}{stance_text}\nStandort: {persona.location}.\n"
    elif effective_type == "validator":
        subtype = getattr(persona, "entity_subtype", "") or getattr(persona, "subtype", "") or "Prüfstelle"
        result = f"Du bist der offizielle Account von {persona.name} ({subtype}).{stance_text}\nStandort: {persona.location}.\n"
    else:
        result = f"Du bist {persona.name}, {persona.age}, {persona.location}, {persona.occupation}.\n"

    # Add tonality hint
    result += f"Tonalität: {_get_tonality_hint(persona)}\n"

    if tags_text:
        result += f"{tags_text}\n"

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

    # Modul 1: Langzeitgedächtnis — Top-10 (war: Top-5)
    memories = list(persona.memory or [])
    if memories:
        # Core Memories zuerst, dann nach emotional_weight
        memories_sorted = sorted(
            memories,
            key=lambda m: (m.get("is_core", False), m.get("emotional_weight", 0)),
            reverse=True,
        )
        result += "\n\n=== Erinnerungen ==="
        for mem in memories_sorted[:10]:
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
    market_context_summary: str | None = None,
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

    system_prompt = _build_agent_system_prompt(market_context_summary)

    try:
        async with semaphore:
            return await provider.call_tool(
                tier="fast",
                system=system_prompt,
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

        # Modul 2: Opinion Dimensions Update mit Bounded Confidence
        opinion_shifts = parsed.get("opinion_shifts", {})
        if opinion_shifts:
            dims = dict(state.get("opinion_dimensions", {}))
            convictions = dict(state.get("conviction", {}))
            # Initialisieren falls noch nicht vorhanden
            if not dims:
                dims = _init_opinion_dimensions(persona.is_skeptic or False)
            if not convictions:
                # Initiale Conviction: Skeptiker starten mit höherer Überzeugung
                base_conv = 0.4 if (persona.is_skeptic or False) else 0.2
                convictions = {key: base_conv for key in OPINION_DIMENSIONS_KEYS}

            # Big-Five-Offenheits-Multiplikator
            traits = persona.personality_traits or {}
            openness = traits.get("openness", 0.5)
            openness_multiplier = 1.3 if openness > 0.7 else (0.7 if openness < 0.3 else 1.0)

            for key in OPINION_DIMENSIONS_KEYS:
                delta = float(opinion_shifts.get(key, 0.0))
                current = dims.get(key, 0.0)
                conviction = convictions.get(key, 0.2)

                # Bounded Confidence: Shift nur wenn Delta klein genug
                # Je höher die Conviction, desto kleiner der akzeptierte Shift
                confidence_threshold = 0.6 * (1.0 - conviction * 0.5)
                if abs(delta) > confidence_threshold:
                    # Post-Meinung zu weit entfernt — ignorieren oder abschwächen
                    delta *= 0.1  # Stark abgeschwächt statt komplett ignoriert

                # Max erlaubter Shift sinkt mit Conviction
                max_shift = 0.3 * (1.0 - conviction * 0.7)
                delta = max(-max_shift, min(max_shift, delta))
                delta *= openness_multiplier

                new_val = max(-1.0, min(1.0, current + delta))
                dims[key] = new_val

                # Conviction-Update: Bestätigung stärkt, Widerspruch schwächt
                if delta != 0:
                    if (current > 0 and delta > 0) or (current < 0 and delta < 0):
                        # Bestätigung: Conviction steigt
                        convictions[key] = min(1.0, conviction + 0.03)
                    else:
                        # Widerspruch: Conviction sinkt
                        convictions[key] = max(0.0, conviction - 0.05)

            state["opinion_dimensions"] = dims
            state["conviction"] = convictions

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
    market_context_summary: str | None = None,
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

    # --- v1.1: Process Trigger Events for this day ---
    trigger_events = []
    try:
        trigger_events = await _process_trigger_events(simulation_id, ingame_day, db)
    except Exception as e:
        logger.warning(f"Trigger-Event-Processing fehlgeschlagen: {e}")

    # Build trigger context for prompts
    trigger_context = ""
    if trigger_events:
        trigger_lines = []
        for te in trigger_events:
            trigger_lines.append(f"[{te['event_type'].upper()}] {te['title']}")
            if te.get('content'):
                trigger_lines.append(f"  {te['content'][:200]}")
        trigger_context = "\n=== AKTUELLE EREIGNISSE ===\n" + "\n".join(trigger_lines) + "\n=== ENDE EREIGNISSE ===\n"

    # Combine market context with trigger context
    effective_context = market_context_summary or ""
    if trigger_context:
        effective_context = (effective_context + "\n" + trigger_context).strip()

    logger.debug(
        f"Tick {tick_number}: {len(personas)} Personas, "
        f"{len(existing_posts)} Posts (Tage {min_day}-{ingame_day})"
    )

    # --- Polarization-Index vom vorherigen Tick laden (für Konsens-Bremse) ---
    prev_polarization = 1.0  # Default: keine Konsens-Bremse
    if tick_number > 1:
        prev_tick_result = await db.execute(
            select(SimulationTick)
            .where(SimulationTick.simulation_id == simulation_id)
            .where(SimulationTick.tick_number == tick_number - 1)
        )
        prev_tick = prev_tick_result.scalar_one_or_none()
        if prev_tick and prev_tick.snapshot:
            prev_polarization = prev_tick.snapshot.get("polarization_index", 1.0)

    # --- Automatische Contrarian-Injection an Tag 7 und 14 ---
    total_ticks = sim.total_ticks or 15
    contrarian_days = {max(1, total_ticks // 2), max(1, total_ticks * 3 // 4)}
    if ingame_day in contrarian_days and prev_polarization < 0.2:
        try:
            from app.simulation.stress_test import inject_contrarian_posts
            injected = await inject_contrarian_posts(simulation_id, db, ingame_day, count=2)
            if injected:
                logger.info(
                    f"Tick {tick_number}: {len(injected)} Contrarian-Posts injiziert "
                    f"(Polarization={prev_polarization:.3f})"
                )
                # Posts neu laden nach Injection
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
                existing_posts = list(posts_result.scalars().all())
        except Exception as e:
            logger.warning(f"Contrarian-Injection fehlgeschlagen: {e}")

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

        # v1.1: Filter personas by activation latency and posting probability
        active_wave_personas = [p for p in wave_personas if _should_persona_act(p, ingame_day)]

        # If trigger events exist, boost activation for affected types
        if trigger_events:
            for p in wave_personas:
                if p not in active_wave_personas:
                    actor_type = getattr(p, 'actor_type', 'private_person') or 'private_person'
                    for te in trigger_events:
                        if actor_type in (te.get('affected_segments') or []):
                            active_wave_personas.append(p)
                            break

        if not active_wave_personas:
            continue

        # --- Feeds bauen mit aktuellem Post-Stand ---
        feeds = {
            str(p.id): build_feed(p, all_posts, ingame_day, all_personas=personas, polarization_index=prev_polarization)
            for p in active_wave_personas
        }

        # --- Persona-History bauen (eigene Posts + erhaltene Kommentare) ---
        histories = {
            str(p.id): _get_persona_history(p, all_posts)
            for p in active_wave_personas
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
                    market_context_summary=effective_context or None,
                )
                for p in active_wave_personas
            ],
            return_exceptions=True,
        )

        # --- Ergebnisse verarbeiten: Multi-Action + DB-Writes ---
        for persona, action_result in zip(active_wave_personas, results):
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

    # --- v1.1: Stagnation Detection ---
    stagnation_events = []
    stagnation_mode = "mild"  # Default; will be read from simulation config
    try:
        sim_obj = await db.get(Simulation, simulation_id)
        stagnation_mode = getattr(sim_obj, 'stagnation_mode', 'mild') or 'mild'
    except Exception:
        pass

    if stagnation_mode != "off" and tick_number > 5:
        # Load recent tick snapshots
        recent_ticks_result = await db.execute(
            select(SimulationTick)
            .where(SimulationTick.simulation_id == simulation_id)
            .order_by(SimulationTick.tick_number.desc())
            .limit(5)
        )
        recent_ticks = recent_ticks_result.scalars().all()
        recent_snapshots = [t.snapshot for t in recent_ticks if t.snapshot]

        if _detect_stagnation(recent_snapshots):
            stagnation_events = await _auto_reactivate(
                simulation_id, ingame_day, db, personas, stagnation_mode
            )

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
            # v1.1 additions
            "trigger_events": [te["title"] for te in trigger_events] if trigger_events else [],
            "stagnation_detected": bool(stagnation_events),
            "stagnation_actions": stagnation_events,
        },
    )
    db.add(tick)

    await db.flush()

    return tick
