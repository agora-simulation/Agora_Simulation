from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Persona
from app.schemas import PersonaRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[PersonaRead])
async def list_personas(
    simulation_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    is_skeptic: bool | None = Query(None),
    actor_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PersonaRead]:
    query = select(Persona).where(Persona.simulation_id == simulation_id)
    if is_skeptic is not None:
        query = query.where(Persona.is_skeptic == is_skeptic)
    if actor_type is not None:
        query = query.where(Persona.actor_type == actor_type)

    # Total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Paginierte Items
    result = await db.execute(
        query.order_by(Persona.created_at.asc()).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/{persona_id}", response_model=PersonaRead)
async def get_persona(
    persona_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PersonaRead:
    result = await db.execute(
        select(Persona).where(Persona.id == persona_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona nicht gefunden")
    return persona
