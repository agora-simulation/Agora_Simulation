"""
Provider-Registry CRUD + Connectivity-Test + Presets + Kostenvorschau + Capabilities.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.provider import LLMProviderRegistry
from app.schemas.provider import (
    CostEstimateRequest,
    CostEstimateResponse,
    DiscoveredModel,
    ModelCapabilities,
    ParamCapability,
    PhaseBreakdown,
    PresetInfo,
    PresetPhaseInfo,
    ProviderCapabilities,
    ProviderCreate,
    ProviderRead,
    ProviderUpdate,
)
from app.utils.crypto import encrypt_api_key, decrypt_api_key

router = APIRouter()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[ProviderRead])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LLMProviderRegistry).order_by(LLMProviderRegistry.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=ProviderRead, status_code=201)
async def create_provider(
    body: ProviderCreate,
    db: AsyncSession = Depends(get_db),
):
    # Wenn is_default, alle anderen Default-Flags zurücksetzen
    if body.is_default:
        await db.execute(
            sa_update(LLMProviderRegistry).values(is_default=False)
        )

    provider = LLMProviderRegistry(
        name=body.name,
        provider_type=body.provider_type,
        api_key_encrypted=encrypt_api_key(body.api_key),
        base_url=body.base_url,
        is_default=body.is_default,
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return provider


# ---------------------------------------------------------------------------
# Presets (MUSS vor /{provider_id} stehen, sonst Route-Konflikt)
# ---------------------------------------------------------------------------

_PRESETS: dict[str, dict] = {
    "budget": {
        "label": "Budget",
        "description": "Günstigste Option: Fast-Modelle überall",
        "persona_generation": {"model_tier": "fast", "temperature": 0.9},
        "agent_actions":      {"model_tier": "fast", "temperature": 0.7},
        "state_updates":      {"model_tier": "fast", "temperature": 0.5},
        "analysis_reports":   {"model_tier": "fast", "temperature": 0.3},
    },
    "balanced": {
        "label": "Balanced",
        "description": "Smart-Modelle für Generierung und Reports, Fast für Ticks",
        "persona_generation": {"model_tier": "smart", "temperature": 0.8},
        "agent_actions":      {"model_tier": "fast",  "temperature": 0.7},
        "state_updates":      {"model_tier": "fast",  "temperature": 0.5},
        "analysis_reports":   {"model_tier": "smart", "temperature": 0.3},
    },
    "quality": {
        "label": "Quality",
        "description": "Smart-Modelle überall, niedrigere Temperatures für Konsistenz",
        "persona_generation": {"model_tier": "smart", "temperature": 0.7},
        "agent_actions":      {"model_tier": "smart", "temperature": 0.6},
        "state_updates":      {"model_tier": "smart", "temperature": 0.4},
        "analysis_reports":   {"model_tier": "smart", "temperature": 0.2},
    },
}


@router.get("/presets", response_model=list[PresetInfo])
async def list_presets():
    return [
        PresetInfo(
            id=key,
            label=val["label"],
            description=val["description"],
            persona_generation=PresetPhaseInfo(**val["persona_generation"]),
            agent_actions=PresetPhaseInfo(**val["agent_actions"]),
            state_updates=PresetPhaseInfo(**val["state_updates"]),
            analysis_reports=PresetPhaseInfo(**val["analysis_reports"]),
        )
        for key, val in _PRESETS.items()
    ]


# ---------------------------------------------------------------------------
# Capabilities (MUSS vor /{provider_id} stehen)
# ---------------------------------------------------------------------------

_SUPPORTED = lambda default=None, mn=None, mx=None: ParamCapability(supported=True, default=default, min=mn, max=mx)
_UNSUPPORTED = lambda reason: ParamCapability(supported=False, reason=reason)

_CAPABILITIES: list[ProviderCapabilities] = [
    ProviderCapabilities(
        provider_type="anthropic",
        display_name="Anthropic Claude",
        supports_base_url=False,
        notes=[
            "Claude 4.x Modelle ignorieren temperature, top_p und top_k — Sampling wird intern gesteuert.",
            "Prompt-Caching (ephemeral) wird automatisch genutzt und spart Kosten bei wiederholten Calls.",
        ],
        models=[
            ModelCapabilities(
                model_id="claude-haiku-4-5-20251001", label="Claude Haiku 4.5", tier="fast",
                provider_type="anthropic",
                temperature=_UNSUPPORTED("Claude 4.x steuert Sampling intern — Temperature hat keinen Effekt."),
                top_p=_UNSUPPORTED("Claude 4.x unterstuetzt kein Nucleus Sampling."),
                top_k=_UNSUPPORTED("Claude 4.x ignoriert top_k aktuell."),
                system_prompt=_SUPPORTED(), caching=_SUPPORTED(),
                max_output_tokens=8192,
                pricing_input_per_1m=1.00, pricing_output_per_1m=5.00,
            ),
            ModelCapabilities(
                model_id="claude-sonnet-4-6", label="Claude Sonnet 4.6", tier="smart",
                provider_type="anthropic",
                temperature=_UNSUPPORTED("Claude 4.x steuert Sampling intern — Temperature hat keinen Effekt."),
                top_p=_UNSUPPORTED("Claude 4.x unterstuetzt kein Nucleus Sampling."),
                top_k=_UNSUPPORTED("Claude 4.x ignoriert top_k aktuell."),
                system_prompt=_SUPPORTED(), caching=_SUPPORTED(),
                max_output_tokens=16384,
                pricing_input_per_1m=3.00, pricing_output_per_1m=15.00,
            ),
            ModelCapabilities(
                model_id="claude-opus-4-7", label="Claude Opus 4.7", tier="smart",
                provider_type="anthropic",
                temperature=_UNSUPPORTED("Claude 4.x steuert Sampling intern — Temperature hat keinen Effekt."),
                top_p=_UNSUPPORTED("Claude 4.x unterstuetzt kein Nucleus Sampling."),
                top_k=_UNSUPPORTED("Claude 4.x ignoriert top_k aktuell."),
                system_prompt=_SUPPORTED(), caching=_SUPPORTED(),
                max_output_tokens=32768,
                pricing_input_per_1m=5.00, pricing_output_per_1m=25.00,
            ),
        ],
    ),
    ProviderCapabilities(
        provider_type="openai",
        display_name="OpenAI GPT",
        supports_base_url=True,
        notes=[
            "Reasoning-Modelle (o1, o3, o4) unterstuetzen keine Sampling-Parameter.",
            "GPT-5-mini unterstuetzt keine Temperature ungleich 1.",
            "top_k ist bei keinem OpenAI-Modell verfuegbar.",
            "Caching erfolgt automatisch ab ~1000 Token Prefix-Laenge.",
        ],
        models=[
            ModelCapabilities(
                model_id="gpt-4o-mini", label="GPT-4o-mini", tier="fast",
                provider_type="openai",
                temperature=_SUPPORTED(default=0.7, mn=0.0, mx=2.0),
                top_p=_SUPPORTED(default=1.0, mn=0.0, mx=1.0),
                top_k=_UNSUPPORTED("OpenAI unterstuetzt kein top_k Sampling."),
                system_prompt=_SUPPORTED(), caching=_SUPPORTED(),
                max_output_tokens=12000,
                pricing_input_per_1m=0.15, pricing_output_per_1m=0.60,
            ),
            ModelCapabilities(
                model_id="gpt-5-mini", label="GPT-5-mini", tier="fast",
                provider_type="openai",
                temperature=_UNSUPPORTED("GPT-5-mini unterstuetzt keine Temperature-Einstellung."),
                top_p=_SUPPORTED(default=1.0, mn=0.0, mx=1.0),
                top_k=_UNSUPPORTED("OpenAI unterstuetzt kein top_k Sampling."),
                system_prompt=_SUPPORTED(), caching=_SUPPORTED(),
                max_output_tokens=12000,
                pricing_input_per_1m=0.75, pricing_output_per_1m=4.50,
            ),
            ModelCapabilities(
                model_id="gpt-4o", label="GPT-4o", tier="smart",
                provider_type="openai",
                temperature=_SUPPORTED(default=0.7, mn=0.0, mx=2.0),
                top_p=_SUPPORTED(default=1.0, mn=0.0, mx=1.0),
                top_k=_UNSUPPORTED("OpenAI unterstuetzt kein top_k Sampling."),
                system_prompt=_SUPPORTED(), caching=_SUPPORTED(),
                max_output_tokens=12000,
                pricing_input_per_1m=2.50, pricing_output_per_1m=10.00,
            ),
            ModelCapabilities(
                model_id="gpt-5", label="GPT-5", tier="smart",
                provider_type="openai",
                temperature=_SUPPORTED(default=0.7, mn=0.0, mx=2.0),
                top_p=_SUPPORTED(default=1.0, mn=0.0, mx=1.0),
                top_k=_UNSUPPORTED("OpenAI unterstuetzt kein top_k Sampling."),
                system_prompt=_SUPPORTED(), caching=_SUPPORTED(),
                max_output_tokens=12000,
                pricing_input_per_1m=2.50, pricing_output_per_1m=15.00,
            ),
        ],
    ),
    ProviderCapabilities(
        provider_type="ollama",
        display_name="Ollama (Lokal)",
        supports_base_url=True,
        supports_api_key=False,
        notes=[
            "Lokale Ausfuehrung — keine API-Kosten, aber abhaengig von Hardware.",
            "Alle Sampling-Parameter werden unterstuetzt.",
            "Modelle muessen lokal installiert sein (ollama pull).",
            "Verfuegbare Modelle werden dynamisch abgefragt ueber GET /providers/{id}/models.",
        ],
        models=[
            ModelCapabilities(
                model_id="qwen2.5:7b", label="Qwen 2.5 7B", tier="fast",
                provider_type="ollama",
                temperature=_SUPPORTED(default=0.7, mn=0.0, mx=2.0),
                top_p=_SUPPORTED(default=0.9, mn=0.0, mx=1.0),
                top_k=_SUPPORTED(default=40, mn=1, mx=200),
                system_prompt=_SUPPORTED(), caching=_UNSUPPORTED("Ollama hat kein Prompt-Caching."),
                max_output_tokens=8192,
                pricing_input_per_1m=0.0, pricing_output_per_1m=0.0,
            ),
            ModelCapabilities(
                model_id="llama3.1:8b", label="Llama 3.1 8B", tier="smart",
                provider_type="ollama",
                temperature=_SUPPORTED(default=0.7, mn=0.0, mx=2.0),
                top_p=_SUPPORTED(default=0.9, mn=0.0, mx=1.0),
                top_k=_SUPPORTED(default=40, mn=1, mx=200),
                system_prompt=_SUPPORTED(), caching=_UNSUPPORTED("Ollama hat kein Prompt-Caching."),
                max_output_tokens=8192,
                pricing_input_per_1m=0.0, pricing_output_per_1m=0.0,
            ),
        ],
    ),
]


@router.get("/capabilities", response_model=list[ProviderCapabilities])
async def get_capabilities():
    """Gibt die Capabilities aller Provider-Typen und ihrer Modelle zurück.

    Das Frontend nutzt diese Daten um:
    - Nicht-unterstützte Parameter auszublenden oder zu disablen
    - Tooltips mit Erklärungen anzuzeigen warum ein Feld nicht verfügbar ist
    - Sinnvolle Defaults pro Modell vorzuschlagen
    """
    return _CAPABILITIES


# ---------------------------------------------------------------------------
# Kostenvorschau (MUSS vor /{provider_id} stehen)
# ---------------------------------------------------------------------------

# Statische Preistabelle: USD pro 1M Tokens (input / output) — Stand April 2026
_PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-haiku-4-5-20251001": {"input": 1.00,  "output": 5.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    "claude-opus-4-7":           {"input": 5.00,  "output": 25.00},
    # OpenAI
    "gpt-4o-mini":               {"input": 0.15,  "output": 0.60},
    "gpt-5-mini":                {"input": 0.75,  "output": 4.50},
    "gpt-4o":                    {"input": 2.50,  "output": 10.00},
    "gpt-5":                     {"input": 2.50,  "output": 15.00},
    # Ollama (lokal = kostenlos)
    "qwen2.5:7b":                {"input": 0.0,   "output": 0.0},
    "llama3.1:8b":               {"input": 0.0,   "output": 0.0},
}

# Durchschnittliche Token-Schätzungen pro Phase
_TOKEN_ESTIMATES: dict[str, dict] = {
    "persona_generation": {"input": 800,  "output": 350, "per": "persona"},
    "agent_actions":      {"input": 600,  "output": 200, "per": "persona_tick"},
    "state_updates":      {"input": 400,  "output": 100, "per": "persona_tick"},
    "analysis_reports":   {"input": 8000, "output": 4000, "per": "simulation"},
}


@router.post("/estimate-cost", response_model=CostEstimateResponse)
async def estimate_cost(body: CostEstimateRequest):
    total = 0.0
    breakdown: dict[str, PhaseBreakdown] = {}
    per_provider: dict[str, float] = {}

    for phase_name in ("persona_generation", "agent_actions", "state_updates", "analysis_reports"):
        phase_config = getattr(body.provider_config, phase_name)
        est = _TOKEN_ESTIMATES[phase_name]

        # Anzahl Calls berechnen
        if est["per"] == "persona":
            calls = body.persona_count
        elif est["per"] == "persona_tick":
            calls = body.persona_count * body.tick_count
        else:  # simulation
            calls = 1

        phase_cost = 0.0
        total_weight = sum(e.weight for e in phase_config.entries)

        for entry in phase_config.entries:
            weight_frac = entry.weight / total_weight if total_weight > 0 else 1.0
            pricing = _PRICING.get(entry.model, {"input": 0.0, "output": 0.0})
            entry_calls = calls * weight_frac
            cost = (
                entry_calls * est["input"] * pricing["input"] / 1_000_000
                + entry_calls * est["output"] * pricing["output"] / 1_000_000
            )
            phase_cost += cost

            # Per-Provider Aggregation (nach provider_id)
            pid = str(entry.provider_id)
            per_provider[pid] = per_provider.get(pid, 0.0) + cost

        breakdown[phase_name] = PhaseBreakdown(
            calls=calls,
            estimated_usd=round(phase_cost, 4),
        )
        total += phase_cost

    return CostEstimateResponse(
        total_estimated_usd=round(total, 4),
        breakdown=breakdown,
        per_provider={k: round(v, 4) for k, v in per_provider.items()},
    )


# ---------------------------------------------------------------------------
# Parametrisierte Routes (nach statischen!)
# ---------------------------------------------------------------------------

@router.get("/{provider_id}", response_model=ProviderRead)
async def get_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(LLMProviderRegistry, provider_id)
    if not provider:
        raise HTTPException(404, detail="Provider nicht gefunden")
    return provider


@router.put("/{provider_id}", response_model=ProviderRead)
async def update_provider(
    provider_id: UUID,
    body: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(LLMProviderRegistry, provider_id)
    if not provider:
        raise HTTPException(404, detail="Provider nicht gefunden")

    if body.name is not None:
        provider.name = body.name
    if body.api_key is not None:
        provider.api_key_encrypted = encrypt_api_key(body.api_key)
    if body.base_url is not None:
        provider.base_url = body.base_url
    if body.is_default is not None:
        if body.is_default:
            await db.execute(
                sa_update(LLMProviderRegistry).values(is_default=False)
            )
        provider.is_default = body.is_default

    await db.flush()
    await db.refresh(provider)
    return provider


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(LLMProviderRegistry, provider_id)
    if not provider:
        raise HTTPException(404, detail="Provider nicht gefunden")
    await db.delete(provider)


# ---------------------------------------------------------------------------
# Connectivity-Test (parametrisierte Route)
# ---------------------------------------------------------------------------

@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(LLMProviderRegistry, provider_id)
    if not provider:
        raise HTTPException(404, detail="Provider nicht gefunden")

    api_key = decrypt_api_key(provider.api_key_encrypted)

    try:
        if provider.provider_type == "anthropic":
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            resp = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return {"success": True, "message": f"Verbindung OK — Modell: {resp.model}"}

        elif provider.provider_type == "openai":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_completion_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return {"success": True, "message": f"Verbindung OK — Modell: {resp.model}"}

        elif provider.provider_type == "ollama":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key="ollama",
                base_url=provider.base_url or "http://localhost:11434/v1",
            )
            models = await client.models.list()
            model_names = [m.id for m in models.data[:5]]
            return {"success": True, "message": f"Verbindung OK — Modelle: {', '.join(model_names)}"}

        else:
            raise HTTPException(400, detail=f"Unbekannter Provider-Typ: {provider.provider_type}")

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": f"Verbindung fehlgeschlagen: {str(e)}"}


@router.get("/{provider_id}/models", response_model=list[DiscoveredModel])
async def discover_models(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Listet verfügbare Modelle für einen Provider.

    - Ollama: Dynamische Abfrage via API (zeigt lokal installierte Modelle)
    - Anthropic/OpenAI: Gibt die statische Modell-Liste zurück
    """
    provider = await db.get(LLMProviderRegistry, provider_id)
    if not provider:
        raise HTTPException(404, detail="Provider nicht gefunden")

    # Statische Modelle aus Capabilities
    caps = next((c for c in _CAPABILITIES if c.provider_type == provider.provider_type), None)
    static_models = [
        DiscoveredModel(model_id=m.model_id, label=m.label, size=None)
        for m in (caps.models if caps else [])
    ]

    if provider.provider_type != "ollama":
        return static_models

    # Ollama: Dynamische Abfrage
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key="ollama",
            base_url=provider.base_url or "http://localhost:11434/v1",
        )
        models_response = await client.models.list()
        discovered = [
            DiscoveredModel(
                model_id=m.id,
                label=m.id.replace(":", " ").title(),
                size=None,
            )
            for m in models_response.data
        ]
        # Statische Modelle + dynamisch entdeckte (ohne Duplikate)
        seen = {m.model_id for m in discovered}
        for s in static_models:
            if s.model_id not in seen:
                discovered.append(s)
        return discovered
    except Exception as e:
        # Fallback auf statische Liste
        return static_models
