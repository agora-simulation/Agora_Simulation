"""v1.1: Crowd Layer Read-Only Router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.crowd_state import CrowdState
from app.schemas.crowd import CrowdStateRead

router = APIRouter()


@router.get("/{simulation_id}", response_model=list[CrowdStateRead])
async def get_crowd_states(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CrowdStateRead]:
    result = await db.execute(
        select(CrowdState)
        .where(CrowdState.simulation_id == simulation_id)
        .order_by(CrowdState.tick)
    )
    return result.scalars().all()


@router.get("/{simulation_id}/latest", response_model=CrowdStateRead)
async def get_latest_crowd_state(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CrowdStateRead:
    result = await db.execute(
        select(CrowdState)
        .where(CrowdState.simulation_id == simulation_id)
        .order_by(CrowdState.tick.desc())
        .limit(1)
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="Keine Crowd-Daten vorhanden")
    return state


@router.get("/{simulation_id}/platform/{platform_id}", response_model=list[CrowdStateRead])
async def get_crowd_by_platform(
    simulation_id: UUID,
    platform_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CrowdStateRead]:
    result = await db.execute(
        select(CrowdState)
        .where(CrowdState.simulation_id == simulation_id)
        .where(CrowdState.platform_id == platform_id)
        .order_by(CrowdState.tick)
    )
    return result.scalars().all()
