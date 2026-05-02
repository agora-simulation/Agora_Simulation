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

logger = logging.getLogger("simulator.chat")
router = APIRouter()


def _build_chat_system_prompt(persona: Persona) -> str:
    """Baut den System-Prompt für den Chat — mit Memory und Opinion-Dimensionen."""
    current_state: dict = persona.current_state or {}

    # Basis-Profil
    prompt = (
        f"Du bist {persona.name}, {persona.age} Jahre alt, wohnhaft in {persona.location}.\n"
        f"Beruf: {persona.occupation}\n\n"
        f"Deine Persönlichkeit: {persona.personality}\n"
        f"Deine Werte: {', '.join(persona.values or [])}\n"
        f"Dein Kommunikationsstil: {persona.communication_style}\n\n"
        f"Deine Erfahrung aus der Simulation:\n"
        f"Meinungsentwicklung: {current_state.get('opinion_evolution', persona.initial_opinion)}\n"
        f"Aktuelle Stimmung: {current_state.get('mood', 'neutral')}\n"
        f"Letzte Aktivitäten: {json.dumps(current_state.get('recent_actions', []), ensure_ascii=False)}\n"
    )

    # Modul 1: Langzeitgedächtnis — alle Erinnerungen für den Chat
    memories = list(persona.memory or [])
    if memories:
        memories_sorted = sorted(memories, key=lambda m: m.get("emotional_weight", 0), reverse=True)
        prompt += "\n=== Deine Erinnerungen aus der Simulation ===\n"
        for mem in memories_sorted:
            weight = mem.get("emotional_weight", 0)
            weight_label = "hoch" if weight >= 0.7 else ("mittel" if weight >= 0.4 else "niedrig")
            prompt += f"[Tag {mem.get('tick', '?')}] {mem.get('summary', '')} (emotional: {weight_label})\n"

    # Modul 2: Mehrdimensionale Meinung
    opinion_dims = current_state.get("opinion_dimensions", {})
    if opinion_dims:
        label_map = {
            "product_quality": "Produktqualität",
            "price_fairness": "Preis-Leistung",
            "brand_trust": "Markenvertrauen",
            "innovation": "Innovation",
            "ethical_concerns": "Ethische Bedenken",
            "social_proof": "Sozialer Einfluss",
            "personal_relevance": "Persönliche Relevanz",
        }
        prompt += "\n=== Deine Einstellung zum Produkt (intern) ===\n"
        for key, label in label_map.items():
            val = opinion_dims.get(key)
            if val is not None:
                desc = "sehr positiv" if val >= 0.6 else ("eher positiv" if val >= 0.2 else
                       "neutral" if val >= -0.2 else "eher negativ" if val >= -0.6 else "sehr negativ")
                prompt += f"{label}: {desc} ({val:.1f})\n"

    prompt += (
        "\nAntworte IMMER in der ersten Person, konsistent mit deiner Persönlichkeit.\n"
        "Sei authentisch — du musst nicht höflich sein wenn du das nicht bist.\n"
        "Wenn du Skeptiker bist, zeige das deutlich.\n"
        "Referenziere deine Erinnerungen wenn relevant.\n"
        "Antworte auf Deutsch, kurz und natürlich (wie in einem echten Gespräch)."
    )

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
