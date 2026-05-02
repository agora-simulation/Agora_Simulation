from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Comment, Post, Reaction
from app.models.content import Platform
from app.schemas import CommentRead, PostRead, ReactionRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[PostRead])
async def list_posts(
    simulation_id: UUID,
    platform: Platform | None = None,
    ingame_day: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PostRead]:
    query = select(Post).where(Post.simulation_id == simulation_id)
    if platform is not None:
        query = query.where(Post.platform == platform)
    if ingame_day is not None:
        query = query.where(Post.ingame_day == ingame_day)

    # Total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Paginierte Items mit Author-Relation
    result = await db.execute(
        query.options(selectinload(Post.author))
        .order_by(Post.ingame_day.asc())
        .limit(limit)
        .offset(offset)
    )
    posts = result.scalars().all()

    # author_name und is_skeptic aus der Relation ableiten
    items = []
    for post in posts:
        read = PostRead.model_validate(post)
        if post.author:
            read.author_name = post.author.name
            read.is_skeptic = post.author.is_skeptic
        items.append(read)

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/{post_id}/comments", response_model=list[CommentRead])
async def list_comments(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CommentRead]:
    # Prüfe ob Post existiert
    post_result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    if not post_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Post nicht gefunden")

    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id)
        .order_by(Comment.ingame_day.asc())
    )
    return result.scalars().all()


@router.get("/{post_id}/reactions", response_model=list[ReactionRead])
async def list_reactions(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ReactionRead]:
    # Prüfe ob Post existiert
    post_result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    if not post_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Post nicht gefunden")

    result = await db.execute(
        select(Reaction)
        .where(Reaction.post_id == post_id)
        .order_by(Reaction.ingame_day.asc())
    )
    return result.scalars().all()
