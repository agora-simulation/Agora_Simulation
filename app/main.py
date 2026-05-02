import logging
import time as _time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers import simulations, personas, posts, analysis
from app.routers import stream
from app.routers import chat
from app.routers import admin
from app.routers import export
from app.routers import providers
from app.auth import verify_api_key
from app.database import get_db
from app.middleware.logging import RequestLoggingMiddleware, SimulatorFormatter
from app.middleware.errors import register_exception_handlers

_APP_START = _time.time()


def _configure_logging() -> None:
    """Set up root logger with the project's SimulatorFormatter."""
    handler = logging.StreamHandler()
    handler.setFormatter(SimulatorFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    from app.simulation.runner import reset_stale_simulations
    await reset_stale_simulations()
    yield
    from app.database import async_engine
    await async_engine.dispose()


app = FastAPI(
    title="Soziale Simulations-Engine",
    description=(
        "KI-gestützte Marktforschungs-Simulation mit virtuellen Personas.\n\n"
        "## Authentifizierung\n"
        "Alle Endpoints (außer `/`, `/health`) erfordern einen `X-API-Key` Header.\n"
        "Keys werden über `POST /admin/keys` mit dem Admin-Master-Key erstellt.\n\n"
        "## Simulation starten\n"
        "1. `POST /simulations/` — Simulation anlegen\n"
        "2. `POST /simulations/{id}/run` — Simulation starten (läuft im Hintergrund)\n"
        "3. `GET /simulations/{id}/stream` — Live-Fortschritt via SSE\n"
        "4. `GET /analysis/{id}` — Report abrufen\n"
        "5. `POST /personas/{id}/chat` — Mit Persona chatten\n"
    ),
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "simulations", "description": "Simulationen anlegen, starten, verwalten"},
        {"name": "personas", "description": "Virtuelle Personas einer Simulation"},
        {"name": "posts", "description": "Posts, Kommentare und Reaktionen"},
        {"name": "analysis", "description": "Analyse-Reports"},
        {"name": "chat", "description": "Direktes Gespräch mit einzelnen Personas"},
        {"name": "stream", "description": "SSE Live-Updates während der Simulation"},
        {"name": "export", "description": "JSON und CSV Export"},
        {"name": "providers", "description": "LLM-Provider Verwaltung (Registry, Presets, Kosten)"},
        {"name": "admin", "description": "API-Key Verwaltung (Master-Key erforderlich)"},
        {"name": "system", "description": "Health Check und Metriken"},
    ],
)

# --- Middleware (order matters: added last = executed first) ---
from app.config import settings as _settings

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception handlers ---
register_exception_handlers(app)

# --- Routers ---
app.include_router(
    simulations.router,
    prefix="/simulations",
    tags=["simulations"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    personas.router,
    prefix="/personas",
    tags=["personas"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    posts.router,
    prefix="/posts",
    tags=["posts"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["analysis"],
    dependencies=[Depends(verify_api_key)],
)
# SSE stream router — routes already carry the full /simulations/... path
# Auth wird per-Route via verify_api_key_header_or_query gemacht (Header ODER ?api_key=),
# damit Browser-EventSource ohne Custom-Header authentifizieren kann.
app.include_router(
    stream.router,
    prefix="",
    tags=["stream"],
)
# Chat interface for individual personas
app.include_router(
    chat.router,
    prefix="",
    tags=["chat"],
    dependencies=[Depends(verify_api_key)],
)
# Provider registry — LLM Provider CRUD, Presets, Cost Estimation
app.include_router(
    providers.router,
    prefix="/providers",
    tags=["providers"],
    dependencies=[Depends(verify_api_key)],
)
# Admin router — secured by separate master key, no API-key auth
app.include_router(admin.router, prefix="/admin", tags=["admin"])
# Export router — JSON and CSV downloads
app.include_router(
    export.router,
    prefix="",
    tags=["export"],
    dependencies=[Depends(verify_api_key)],
)


@app.get("/", tags=["system"])
async def root():
    return {"status": "ok", "service": "Soziale Simulations-Engine", "version": "0.1.0"}


@app.get("/health", tags=["system"])
async def health(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(503, detail="Database nicht erreichbar")
    return {
        "status": "healthy",
        "db": "ok" if db_ok else "error",
        "uptime_seconds": int(_time.time() - _APP_START),
    }


@app.get("/metrics", tags=["system"], dependencies=[Depends(verify_api_key)])
async def metrics(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func, select
    from app.models import Simulation, SimulationStatus, Persona, Post, ApiKey
    status_counts = {}
    for s in SimulationStatus:
        r = await db.execute(select(func.count()).where(Simulation.status == s))
        status_counts[s.value] = r.scalar_one()
    personas = (await db.execute(select(func.count()).select_from(Persona))).scalar_one()
    posts = (await db.execute(select(func.count()).select_from(Post))).scalar_one()
    keys = (await db.execute(select(func.count()).where(ApiKey.is_active == True))).scalar_one()
    return {
        "simulations": {"total": sum(status_counts.values()), **status_counts},
        "personas_total": personas,
        "posts_total": posts,
        "active_api_keys": keys,
        "uptime_seconds": int(_time.time() - _APP_START),
    }
