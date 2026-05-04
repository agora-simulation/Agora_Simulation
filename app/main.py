import logging
import os
import time as _time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers import simulations, personas, posts, analysis
from app.routers import stream
from app.routers import chat
from app.routers import admin
from app.routers import export
from app.routers import providers
# v1.1
from app.routers import platforms, trigger_events, research_snapshots, templates, crowd
from app.auth import verify_api_key
from app.database import get_db
from app.middleware.logging import RequestLoggingMiddleware, AgoraFormatter
from app.middleware.errors import register_exception_handlers

_APP_START = _time.time()


def _configure_logging() -> None:
    """Set up root logger with the project's AgoraFormatter."""
    handler = logging.StreamHandler()
    handler.setFormatter(AgoraFormatter())
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
        # v1.1
        {"name": "platforms", "description": "Plattform-Layer Verwaltung"},
        {"name": "trigger-events", "description": "Trigger Events / News-Injection"},
        {"name": "research", "description": "Eigenständige Marktrecherchen"},
        {"name": "templates", "description": "Template-System (Verteilung, Tonalität, Trigger-Library)"},
        {"name": "crowd", "description": "Crowd-Layer Daten"},
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
# v1.1 Routers
app.include_router(platforms.router, prefix="/platforms", tags=["platforms"], dependencies=[Depends(verify_api_key)])
app.include_router(trigger_events.router, prefix="/trigger-events", tags=["trigger-events"], dependencies=[Depends(verify_api_key)])
app.include_router(research_snapshots.router, prefix="/research", tags=["research"], dependencies=[Depends(verify_api_key)])
app.include_router(templates.router, prefix="/templates", tags=["templates"], dependencies=[Depends(verify_api_key)])
app.include_router(crowd.router, prefix="/crowd", tags=["crowd"], dependencies=[Depends(verify_api_key)])
# Export router — JSON and CSV downloads
app.include_router(
    export.router,
    prefix="",
    tags=["export"],
    dependencies=[Depends(verify_api_key)],
)


@app.get("/", tags=["system"])
async def root():
    # Wenn Frontend gebaut ist → index.html liefern
    index = Path(__file__).resolve().parent.parent / "static" / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"status": "ok", "service": "Agora Simulations-Engine", "version": "0.1.0"}


@app.get("/api/status", tags=["system"])
async def api_status():
    return {"status": "ok", "service": "Agora Simulations-Engine", "version": "0.1.0"}


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


# --- Static Frontend (Angular SPA) ---
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if _STATIC_DIR.is_dir():
    # Angular Assets (JS, CSS, Icons etc.) — served unter /static/
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets" if (_STATIC_DIR / "assets").is_dir() else _STATIC_DIR), name="assets")

    # SPA Fallback: Alle nicht-API-Routen → index.html (Angular Router übernimmt)
    @app.get("/{path:path}", tags=["system"], include_in_schema=False)
    async def spa_fallback(path: str):
        # API-Pfade nicht abfangen
        file_path = _STATIC_DIR / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")
