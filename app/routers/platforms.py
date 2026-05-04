"""v1.1: Platform Layer CRUD Router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.platform import SimPlatform
from app.schemas.platform import PlatformCreate, PlatformUpdate, PlatformRead

router = APIRouter()


@router.get("/", response_model=list[PlatformRead])
async def list_platforms(
    simulation_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[PlatformRead]:
    """List platforms. Shows globals (simulation_id=NULL) and optionally sim-specific ones."""
    query = select(SimPlatform)
    if simulation_id:
        query = query.where(or_(SimPlatform.simulation_id == simulation_id, SimPlatform.simulation_id.is_(None)))
    else:
        query = query.where(SimPlatform.simulation_id.is_(None))
    result = await db.execute(query.order_by(SimPlatform.name))
    return result.scalars().all()


@router.post("/", response_model=PlatformRead, status_code=201)
async def create_platform(
    body: PlatformCreate,
    db: AsyncSession = Depends(get_db),
) -> PlatformRead:
    platform = SimPlatform(**body.model_dump())
    db.add(platform)
    await db.flush()
    await db.refresh(platform)
    return platform


@router.get("/{platform_id}", response_model=PlatformRead)
async def get_platform(
    platform_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PlatformRead:
    result = await db.execute(select(SimPlatform).where(SimPlatform.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Plattform nicht gefunden")
    return platform


@router.put("/{platform_id}", response_model=PlatformRead)
async def update_platform(
    platform_id: UUID,
    body: PlatformUpdate,
    db: AsyncSession = Depends(get_db),
) -> PlatformRead:
    result = await db.execute(select(SimPlatform).where(SimPlatform.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Plattform nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(platform, key, value)
    await db.flush()
    await db.refresh(platform)
    return platform


@router.delete("/{platform_id}", status_code=204)
async def delete_platform(
    platform_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(SimPlatform).where(SimPlatform.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Plattform nicht gefunden")
    await db.delete(platform)


@router.post("/seed-defaults")
async def seed_defaults(db: AsyncSession = Depends(get_db)) -> dict:
    """Seed default platforms if none exist."""
    result = await db.execute(select(func.count()).select_from(SimPlatform).where(SimPlatform.simulation_id.is_(None)))
    count = result.scalar_one()
    if count > 0:
        return {"message": f"Default-Plattformen existieren bereits ({count})"}

    defaults = [
        SimPlatform(name="Threadit", character="operativ", reach_multiplier=1.0, echo_chamber_strength=0.3, default_engagement_rate=0.4),
        SimPlatform(name="Feedbook", character="institutionell", reach_multiplier=1.2, echo_chamber_strength=0.6, default_engagement_rate=0.25),
    ]
    for p in defaults:
        db.add(p)
    await db.flush()
    return {"message": f"{len(defaults)} Default-Plattformen erstellt"}
