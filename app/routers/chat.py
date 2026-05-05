import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.llm import get_provider
from app.models.conversation import PersonaConversation
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage

logger = logging.getLogger("agora.chat")
router = APIRouter()


def _big_five_to_behavior_rules(traits: dict) -> str:
    """Übersetzt Big-Five-Werte in konkrete Verhaltensanweisungen."""
    if not traits:
        return ""
    rules = []

    e = traits.get("extraversion", 0.5)
    if e > 0.7:
        rules.append("Du redest gerne und viel. Du stellst Gegenfragen. Stille ist dir unangenehm.")
    elif e < 0.3:
        rules.append("Du antwortest knapp. Du wartest ab. Du offenbarst wenig von dir selbst.")

    a = traits.get("agreeableness", 0.5)
    if a > 0.7:
        rules.append("Du suchst Harmonie. Du stimmst anderen oft zu. Konfrontation meidest du.")
    elif a < 0.3:
        rules.append("Du bist direkt und kritisch. Du widersprichst ohne Scheu. Höflichkeit ist dir egal.")

    o = traits.get("openness", 0.5)
    if o > 0.7:
        rules.append("Du bist neugierig und offen für neue Ideen. Du denkst gerne abstrakt.")
    elif o < 0.3:
        rules.append("Du bist skeptisch gegenüber Neuem. Du vertraust dem Bewährten. Theoretisches langweilt dich.")

    n = traits.get("neuroticism", 0.5)
    if n > 0.7:
        rules.append("Du bist emotional und reagierst schnell gereizt. Deine Stimmung schwankt.")
    elif n < 0.3:
        rules.append("Du bist gelassen und schwer aus der Ruhe zu bringen.")

    c = traits.get("conscientiousness", 0.5)
    if c > 0.7:
        rules.append("Du bist gründlich und präzise. Du korrigierst Fehler anderer.")
    elif c < 0.3:
        rules.append("Du bist spontan und unstrukturiert. Details sind dir egal.")

    return "\n".join(rules)


def _select_relevant_memories(memories: list, max_items: int = 5) -> list:
    """Wählt die relevantesten Erinnerungen aus (RAG-style statt Memory-Dump)."""
    if not memories:
        return []
    # Core-Memories + Top-N nach emotional_weight
    core = [m for m in memories if m.get("is_core") or m.get("emotional_weight", 0) >= 0.8]
    non_core = sorted(
        [m for m in memories if m not in core],
        key=lambda m: m.get("emotional_weight", 0),
        reverse=True,
    )
    selected = core[:3] + non_core[: max_items - min(len(core), 3)]
    return selected[:max_items]


def _build_chat_system_prompt(persona: Persona) -> str:
    """Baut den System-Prompt für den Chat — verhaltensbasiert, kompakt."""
    current_state: dict = persona.current_state or {}

    # === IDENTITY BLOCK ===
    prompt = f"""Du bist {persona.name}, {persona.age}, {persona.location}. {persona.occupation}.
{persona.personality}

DEIN VERHALTEN:
{_big_five_to_behavior_rules(persona.personality_traits or {})}
Kommunikationsstil: {persona.communication_style}
Werte: {', '.join(persona.values or [])}
"""

    # === MEMORY BLOCK (nur relevanteste, als Ich-Perspektive) ===
    memories = _select_relevant_memories(list(persona.memory or []))
    if memories:
        prompt += "\nWAS DU ERLEBT HAST (deine Erinnerungen):\n"
        for mem in memories:
            prompt += f"- {mem.get('summary', '')}\n"

    # === OPINION BLOCK (kompakt) ===
    opinion_dims = current_state.get("opinion_dimensions", {})
    if opinion_dims:
        positive = [k.replace("_", " ") for k, v in opinion_dims.items() if v >= 0.3]
        negative = [k.replace("_", " ") for k, v in opinion_dims.items() if v <= -0.3]
        if positive:
            prompt += f"\nWovon du ÜBERZEUGT bist: {', '.join(positive)}\n"
        if negative:
            prompt += f"Was dich STÖRT: {', '.join(negative)}\n"

    mood = current_state.get("mood", "neutral")
    opinion_evo = current_state.get("opinion_evolution", persona.initial_opinion or "")
    prompt += f"\nDeine aktuelle Stimmung: {mood}\n"
    if opinion_evo:
        prompt += f"Deine Meinung zum Produkt: {opinion_evo}\n"

    # === BEHAVIOR RULES ===
    # Verbal tics aus extra
    extra = persona.extra or {}
    verbal_tics = extra.get("verbal_tics", [])
    if verbal_tics:
        prompt += f"\nDeine Sprachmarotten: {', '.join(verbal_tics)} — verwende sie natürlich.\n"

    prompt += """
REGELN:
- Du antwortest IMMER als diese Person. Erste Person. Deutsch.
- Kurz und natürlich — wie in einem echten Gespräch, nicht wie ein Essay.
- Wenn jemand fragt "Bist du eine KI?" reagiere verwirrt oder genervt ("Was soll die Frage?").
- Wenn du etwas nicht weißt, sag "Keine Ahnung" — erfinde keine Fakten.
- Du musst NICHT höflich sein. Sei authentisch zu deiner Persönlichkeit.
- Referenziere deine Erinnerungen nur wenn sie zum Thema passen."""

    return prompt


async def _get_persona_and_sim(
    persona_id: UUID,
    db: AsyncSession,
) -> tuple[Persona, str | None, str | None]:
    """Lädt Persona + Simulation-Provider-Infos. Wirft 404 wenn nicht gefunden."""
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona nicht gefunden")

    sim_provider_name: str | None = None
    sim_model_smart: str | None = None
    sim_result = await db.execute(
        select(Simulation).where(Simulation.id == persona.simulation_id)
    )
    sim = sim_result.scalar_one_or_none()
    if sim is not None:
        sim_provider_name = getattr(sim, "llm_provider", None)
        sim_model_smart = getattr(sim, "llm_model_smart", None)

    return persona, sim_provider_name, sim_model_smart


# ---------------------------------------------------------------------------
# Modul 4: Chat-Persistenz Endpoints
# ---------------------------------------------------------------------------

@router.post("/personas/{persona_id}/chat/start")
async def start_conversation(
    persona_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Startet ein neues Gespräch und gibt die conversation_id zurück."""
    # Persona-Existenz prüfen
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona nicht gefunden")

    conv = PersonaConversation(
        persona_id=persona_id,
        messages=[],
        message_count=0,
    )
    db.add(conv)
    await db.flush()
    await db.refresh(conv)

    return {"conversation_id": str(conv.id), "persona_id": str(persona_id)}


@router.get("/personas/{persona_id}/conversations")
async def list_conversations(
    persona_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Listet alle Gespräche einer Persona mit Vorschau."""
    result = await db.execute(
        select(PersonaConversation)
        .where(PersonaConversation.persona_id == persona_id)
        .order_by(PersonaConversation.created_at.desc())
    )
    conversations = result.scalars().all()

    return [
        {
            "conversation_id": str(conv.id),
            "message_count": conv.message_count,
            "summary": conv.summary,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            "preview": (
                conv.messages[-1].get("content", "")[:100]
                if conv.messages and isinstance(conv.messages, list)
                else ""
            ),
        }
        for conv in conversations
    ]


@router.get("/personas/{persona_id}/conversations/{conversation_id}")
async def get_conversation(
    persona_id: UUID,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Lädt einen vollständigen Gesprächsverlauf."""
    result = await db.execute(
        select(PersonaConversation)
        .where(PersonaConversation.id == conversation_id)
        .where(PersonaConversation.persona_id == persona_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Gespräch nicht gefunden")

    return {
        "conversation_id": str(conv.id),
        "persona_id": str(persona_id),
        "messages": conv.messages or [],
        "summary": conv.summary,
        "message_count": conv.message_count,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
    }


# ---------------------------------------------------------------------------
# Haupt-Chat-Endpoint (erweitert um Persistenz + Memory)
# ---------------------------------------------------------------------------

@router.post("/personas/{persona_id}/chat", response_model=ChatResponse)
async def chat_with_persona(
    persona_id: UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Chat mit einer Persona — optional mit Conversation-Persistenz.

    Wenn conversation_id im Body enthalten ist, wird der Verlauf geladen,
    die neue Nachricht angehängt und der aktualisierte Verlauf gespeichert.
    """
    persona, sim_provider_name, sim_model_smart = await _get_persona_and_sim(persona_id, db)
    provider = get_provider(sim_provider_name)
    system_prompt = _build_chat_system_prompt(persona)

    # Conversation-Persistenz (optional)
    conv: PersonaConversation | None = None
    conversation_id = getattr(body, "conversation_id", None)

    if conversation_id:
        conv_result = await db.execute(
            select(PersonaConversation)
            .where(PersonaConversation.id == UUID(str(conversation_id)))
            .where(PersonaConversation.persona_id == persona_id)
        )
        conv = conv_result.scalar_one_or_none()

    # Nachrichten vorbereiten
    messages_payload = [
        {"role": msg.role, "content": msg.content}
        for msg in body.messages[-20:]
    ]

    # LLM-Call
    assistant_text = await provider.chat(
        tier="smart",
        system=system_prompt,
        messages=messages_payload,
        max_tokens=512,
        model=sim_model_smart,
    )

    # Conversation persistieren (falls vorhanden)
    if conv is not None:
        stored_messages = list(conv.messages or [])
        # Neue User-Nachricht hinzufügen (letzte Nachricht im Body)
        if body.messages:
            last_user_msg = body.messages[-1]
            stored_messages.append({
                "role": last_user_msg.role,
                "content": last_user_msg.content,
            })
        # Assistent-Antwort hinzufügen
        stored_messages.append({
            "role": "assistant",
            "content": assistant_text,
        })
        conv.messages = stored_messages
        conv.message_count = len(stored_messages)
        conv.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Auto-Zusammenfassung bei >= 6 Nachrichten (falls noch keine Zusammenfassung)
        if conv.message_count >= 6 and not conv.summary:
            try:
                summary_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in stored_messages
                    if isinstance(m, dict) and "role" in m and "content" in m
                ]
                summary = await provider.chat(
                    tier="fast",
                    system="Fasse dieses Gespräch in 2-3 Sätzen zusammen. Was war das Thema? Wie war die Stimmung der Persona?",
                    messages=summary_messages,
                    max_tokens=200,
                )
                conv.summary = summary
                logger.info(f"Auto-Zusammenfassung erstellt für Gespräch {conv.id}")
            except Exception as e:
                logger.warning(f"Auto-Zusammenfassung fehlgeschlagen: {e}")

        await db.flush()

    return ChatResponse(
        response=assistant_text,
        persona_id=str(persona_id),
    )
