"""v1.2: Research Snapshots CRUD + Execute Router."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.research_snapshot import ResearchSnapshot
from app.models.provider import LLMProviderRegistry
from app.schemas.research_snapshot import (
    ResearchSnapshotCreate,
    ResearchSnapshotUpdate,
    ResearchSnapshotRead,
    ResearchExecuteRequest,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()
logger = logging.getLogger("agora.research")

DEFAULT_SYSTEM_PROMPT = (
    "Du bist ein erfahrener Marktforschungs-Analyst. "
    "Liefere eine detaillierte, strukturierte Analyse auf Deutsch. "
    "Nutze Ueberschriften, Aufzaehlungen und konkrete Erkenntnisse. "
    "Kennzeichne Annahmen und bewerte die Zuverlaessigkeit deiner Aussagen."
)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/", response_model=PaginatedResponse[ResearchSnapshotRead])
async def list_snapshots(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ResearchSnapshotRead]:
    query = select(ResearchSnapshot)
    if status:
        query = query.where(ResearchSnapshot.status == status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(ResearchSnapshot.created_at.desc()).limit(limit).offset(offset)
    )
    items = result.scalars().all()
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)


@router.post("/", response_model=ResearchSnapshotRead, status_code=201)
async def create_snapshot(
    body: ResearchSnapshotCreate,
    db: AsyncSession = Depends(get_db),
) -> ResearchSnapshotRead:
    snapshot = ResearchSnapshot(**body.model_dump())
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)
    return snapshot


@router.get("/{snapshot_id}", response_model=ResearchSnapshotRead)
async def get_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchSnapshotRead:
    result = await db.execute(select(ResearchSnapshot).where(ResearchSnapshot.id == snapshot_id))
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Research Snapshot nicht gefunden")
    return snapshot


@router.put("/{snapshot_id}", response_model=ResearchSnapshotRead)
async def update_snapshot(
    snapshot_id: UUID,
    body: ResearchSnapshotUpdate,
    db: AsyncSession = Depends(get_db),
) -> ResearchSnapshotRead:
    result = await db.execute(select(ResearchSnapshot).where(ResearchSnapshot.id == snapshot_id))
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Research Snapshot nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(snapshot, key, value)
    await db.flush()
    await db.refresh(snapshot)
    return snapshot


@router.delete("/{snapshot_id}", status_code=204)
async def delete_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(ResearchSnapshot).where(ResearchSnapshot.id == snapshot_id))
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Research Snapshot nicht gefunden")
    await db.delete(snapshot)


@router.post("/{snapshot_id}/approve", response_model=ResearchSnapshotRead)
async def approve_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchSnapshotRead:
    result = await db.execute(select(ResearchSnapshot).where(ResearchSnapshot.id == snapshot_id))
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Research Snapshot nicht gefunden")
    snapshot.status = "approved"
    await db.flush()
    await db.refresh(snapshot)
    return snapshot


@router.post("/{snapshot_id}/execute", response_model=ResearchSnapshotRead)
async def execute_snapshot(
    snapshot_id: UUID,
    body: ResearchExecuteRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> ResearchSnapshotRead:
    """Execute a research snapshot — calls the configured LLM and stores the result."""
    from app.llm.factory import get_provider_by_registry

    # 1. Load snapshot
    result = await db.execute(select(ResearchSnapshot).where(ResearchSnapshot.id == snapshot_id))
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Research Snapshot nicht gefunden")

    if snapshot.status == "running":
        raise HTTPException(status_code=409, detail="Recherche laeuft bereits")

    # 2. Apply overrides from request body
    if body:
        overrides = body.model_dump(exclude_unset=True)
        for key, value in overrides.items():
            setattr(snapshot, key, value)

    # 3. Validate required fields
    if not snapshot.provider_id:
        raise HTTPException(status_code=422, detail="Kein Provider ausgewaehlt")
    if not snapshot.prompt:
        raise HTTPException(status_code=422, detail="Kein Prompt angegeben")

    # 4. Load provider from registry
    provider_result = await db.execute(
        select(LLMProviderRegistry).where(LLMProviderRegistry.id == snapshot.provider_id)
    )
    registry_entry = provider_result.scalar_one_or_none()
    if not registry_entry:
        raise HTTPException(status_code=422, detail="Provider nicht gefunden")

    provider = get_provider_by_registry(registry_entry)

    # 5. Set running state
    snapshot.status = "running"
    snapshot.error = None
    snapshot.result = None
    snapshot.execution_started_at = _utcnow()
    snapshot.execution_finished_at = None
    await db.flush()

    # 6. Execute LLM call
    system = snapshot.system_prompt or DEFAULT_SYSTEM_PROMPT
    try:
        llm_result = await provider.chat(
            tier="smart",
            system=system,
            messages=[{"role": "user", "content": snapshot.prompt}],
            max_tokens=snapshot.max_tokens or 4096,
            model=snapshot.model or None,
            temperature=snapshot.temperature,
        )
        snapshot.result = llm_result
        snapshot.status = "completed"
        snapshot.llm_used = snapshot.model or registry_entry.provider_type
        snapshot.execution_finished_at = _utcnow()
        logger.info("Research %s completed (%s)", snapshot_id, snapshot.llm_used)

    except Exception as exc:
        snapshot.status = "failed"
        snapshot.error = str(exc)
        snapshot.execution_finished_at = _utcnow()
        logger.error("Research %s failed: %s", snapshot_id, exc)

    await db.flush()
    await db.refresh(snapshot)
    return snapshot
