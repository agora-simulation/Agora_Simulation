"""v1.1: Trigger Events CRUD Router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.trigger_event import TriggerEvent
from app.schemas.trigger_event import TriggerEventCreate, TriggerEventRead

router = APIRouter()


@router.get("/", response_model=list[TriggerEventRead])
async def list_trigger_events(
    simulation_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[TriggerEventRead]:
    result = await db.execute(
        select(TriggerEvent)
        .where(TriggerEvent.simulation_id == simulation_id)
        .order_by(TriggerEvent.tick_day)
    )
    return result.scalars().all()


@router.post("/", response_model=TriggerEventRead, status_code=201)
async def create_trigger_event(
    body: TriggerEventCreate,
    db: AsyncSession = Depends(get_db),
) -> TriggerEventRead:
    event = TriggerEvent(**body.model_dump())
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.get("/{event_id}", response_model=TriggerEventRead)
async def get_trigger_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TriggerEventRead:
    result = await db.execute(select(TriggerEvent).where(TriggerEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Trigger-Event nicht gefunden")
    return event


@router.put("/{event_id}", response_model=TriggerEventRead)
async def update_trigger_event(
    event_id: UUID,
    body: TriggerEventCreate,
    db: AsyncSession = Depends(get_db),
) -> TriggerEventRead:
    result = await db.execute(select(TriggerEvent).where(TriggerEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Trigger-Event nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_trigger_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(TriggerEvent).where(TriggerEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Trigger-Event nicht gefunden")
    await db.delete(event)


@router.post("/{simulation_id}/inject", response_model=TriggerEventRead)
async def inject_trigger_event(
    simulation_id: UUID,
    body: TriggerEventCreate,
    db: AsyncSession = Depends(get_db),
) -> TriggerEventRead:
    """Inject a live trigger event into a simulation."""
    from app.models import Simulation, SimulationStatus
    sim_result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = sim_result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden")

    event = TriggerEvent(
        simulation_id=simulation_id,
        tick_day=body.tick_day or (sim.current_tick + 1),
        event_type=body.event_type,
        title=body.title,
        content=body.content,
        affected_segments=body.affected_segments,
        intensity=body.intensity,
        source_attribution=body.source_attribution,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event
