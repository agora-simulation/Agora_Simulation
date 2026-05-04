"""v1.1: Template System CRUD Router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/categories")
async def list_categories() -> list[str]:
    return ["distribution", "tonality", "trigger_library", "research"]


@router.get("/", response_model=PaginatedResponse[TemplateRead])
async def list_templates(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    is_default: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TemplateRead]:
    query = select(Template)
    if category:
        query = query.where(Template.category == category)
    if is_default is not None:
        query = query.where(Template.is_default == is_default)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(Template.category, Template.name).limit(limit).offset(offset)
    )
    items = result.scalars().all()
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)


@router.post("/", response_model=TemplateRead, status_code=201)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> TemplateRead:
    template = Template(**body.model_dump())
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateRead)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TemplateRead:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template nicht gefunden")
    return template


@router.put("/{template_id}", response_model=TemplateRead)
async def update_template(
    template_id: UUID,
    body: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> TemplateRead:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    await db.flush()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template nicht gefunden")
    await db.delete(template)


@router.post("/seed-defaults")
async def seed_defaults(db: AsyncSession = Depends(get_db)) -> dict:
    """Seed all default templates (distribution, tonality, trigger_library, actor_distribution)."""
    from app.schemas.actor_types import DISTRIBUTION_TEMPLATES, TONALITY_TEMPLATES

    created = 0

    # Distribution templates
    for name, dist in DISTRIBUTION_TEMPLATES.items():
        existing = await db.execute(
            select(Template).where(Template.category == "distribution", Template.name == name, Template.is_default == True)
        )
        if not existing.scalar_one_or_none():
            db.add(Template(category="distribution", name=name, is_default=True, content=dist))
            created += 1

    # Tonality templates
    for actor_type, tonality in TONALITY_TEMPLATES.items():
        existing = await db.execute(
            select(Template).where(Template.category == "tonality", Template.name == actor_type, Template.is_default == True)
        )
        if not existing.scalar_one_or_none():
            db.add(Template(category="tonality", name=actor_type, is_default=True, content={"text": tonality}))
            created += 1

    # Trigger-Library templates
    trigger_defaults = {
        "Produktrueckruf": {"event_type": "news_headline", "intensity": "critical", "content": "Ein bekanntes Medium berichtet ueber einen moeglichen Produktrueckruf. Sicherheitsbedenken stehen im Raum.", "affected_segments": ["media", "company", "authority"]},
        "Wettbewerber launcht Alternative": {"event_type": "competitor_action", "intensity": "major", "content": "Ein direkter Wettbewerber bringt ein vergleichbares Produkt zu einem deutlich guenstigeren Preis auf den Markt.", "affected_segments": ["company", "media", "influencer"]},
        "Regulatorische Verschaerfung": {"event_type": "regulatory_change", "intensity": "major", "content": "Neue EU-Verordnung verschaerft Anforderungen an die Branche. Uebergangsfristen sind kurz.", "affected_segments": ["authority", "company", "collective"]},
        "Viraler Social-Media-Vorfall": {"event_type": "social_incident", "intensity": "major", "content": "Ein virales Video zeigt einen negativen Vorfall mit dem Produkt. Millionen Views innerhalb weniger Stunden.", "affected_segments": ["influencer", "media", "private_person"]},
        "Positive Studie veroeffentlicht": {"event_type": "news_headline", "intensity": "minor", "content": "Eine renommierte Forschungseinrichtung veroeffentlicht positive Studienergebnisse zum Produkt.", "affected_segments": ["research_institute", "expert", "media"]},
        "Preissteigerung angekuendigt": {"event_type": "competitor_action", "intensity": "minor", "content": "Das Unternehmen kuendigt eine Preiserhoehung ab naechstem Quartal an.", "affected_segments": ["private_person", "company", "media"]},
        "Validierer gibt Freigabe": {"event_type": "validator_decision", "intensity": "major", "content": "Eine zustaendige Pruefstelle erteilt die offizielle Freigabe/Zertifizierung.", "affected_segments": ["validator", "authority", "company"]},
    }
    for name, trigger in trigger_defaults.items():
        existing = await db.execute(
            select(Template).where(Template.category == "trigger_library", Template.name == name, Template.is_default == True)
        )
        if not existing.scalar_one_or_none():
            db.add(Template(category="trigger_library", name=name, is_default=True, content=trigger))
            created += 1

    await db.flush()
    return {"message": f"{created} Default-Templates erstellt"}
