"""v1.1: Research Snapshots CRUD Router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.research_snapshot import ResearchSnapshot
from app.schemas.research_snapshot import ResearchSnapshotCreate, ResearchSnapshotUpdate, ResearchSnapshotRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


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
