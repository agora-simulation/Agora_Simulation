import csv
import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Simulation, Persona, Post, Comment, Reaction, AnalysisReport, InfluenceEvent

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: load simulation or 404
# ---------------------------------------------------------------------------

async def _get_simulation_or_404(simulation_id: UUID, db: AsyncSession) -> Simulation:
    result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one_or_none()
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


# ---------------------------------------------------------------------------
# Endpoint 1: Full JSON export
# ---------------------------------------------------------------------------

@router.get(
    "/simulations/{simulation_id}/export/json",
    summary="Export simulation as JSON",
    response_class=Response,
)
async def export_simulation_json(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export the complete simulation including personas, posts, comments,
    reactions, and the analysis report as a single JSON file download."""

    # Load simulation with all nested relations in one query set
    sim_result = await db.execute(
        select(Simulation)
        .where(Simulation.id == simulation_id)
        .options(
            selectinload(Simulation.personas),
            selectinload(Simulation.posts).options(
                selectinload(Post.author),
                selectinload(Post.comments).options(
                    selectinload(Comment.author)
                ),
                selectinload(Post.reactions),
            ),
            selectinload(Simulation.reports),
        )
    )
    sim = sim_result.scalar_one_or_none()
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # --- Build personas list ---
    personas_data = [
        {
            "persona_id": str(p.id),
            "name": p.name,
            "age": p.age,
            "location": p.location,
            "occupation": p.occupation,
            "personality": p.personality,
            "values": p.values,
            "communication_style": p.communication_style,
            "initial_opinion": p.initial_opinion,
            "is_skeptic": p.is_skeptic,
            "social_connections": p.social_connections,
            "current_state": p.current_state,
            "extra": p.extra,
            "created_at": str(p.created_at),
        }
        for p in sim.personas
    ]

    # --- Build posts list (with comments + reactions) ---
    posts_data = []
    for post in sim.posts:
        # Aggregate reactions by type
        reactions_agg: dict[str, int] = {"like": 0, "dislike": 0, "share": 0}
        for r in post.reactions:
            rtype = r.reaction_type.value if hasattr(r.reaction_type, "value") else str(r.reaction_type)
            if rtype in reactions_agg:
                reactions_agg[rtype] += 1
            else:
                reactions_agg[rtype] = 1

        comments_data = [
            {
                "comment_id": str(c.id),
                "author_name": c.author.name if c.author else None,
                "content": c.content,
                "ingame_day": c.ingame_day,
                "created_at": str(c.created_at),
            }
            for c in post.comments
        ]

        posts_data.append(
            {
                "post_id": str(post.id),
                "platform": post.platform.value if hasattr(post.platform, "value") else str(post.platform),
                "author_name": post.author.name if post.author else None,
                "author_id": str(post.author_id),
                "is_skeptic": post.author.is_skeptic if post.author else None,
                "ingame_day": post.ingame_day,
                "content": post.content,
                "subreddit": post.subreddit,
                "created_at": str(post.created_at),
                "comments": comments_data,
                "reactions": reactions_agg,
            }
        )

    # --- Influence Events laden ---
    influence_result = await db.execute(
        select(InfluenceEvent)
        .where(InfluenceEvent.simulation_id == simulation_id)
        .order_by(InfluenceEvent.ingame_day)
    )
    influence_events = influence_result.scalars().all()

    influence_data = [
        {
            "id": str(e.id),
            "source_persona_id": str(e.source_persona_id),
            "target_persona_id": str(e.target_persona_id),
            "trigger_post_id": str(e.trigger_post_id) if e.trigger_post_id else None,
            "ingame_day": e.ingame_day,
            "influence_type": e.influence_type,
            "description": e.description,
            "created_at": str(e.created_at),
        }
        for e in influence_events
    ]

    # --- Report ---
    report_data: dict | None = None
    if sim.reports:
        latest = sorted(sim.reports, key=lambda r: r.created_at)[-1]
        report_data = {
            "full_report": latest.full_report,
            "sentiment_over_time": latest.sentiment_over_time,
            "key_turning_points": latest.key_turning_points,
            "criticism_points": latest.criticism_points,
            "opportunities": latest.opportunities,
            "target_segment_analysis": latest.target_segment_analysis,
            "unexpected_findings": latest.unexpected_findings,
            "influence_network": latest.influence_network,
            "platform_dynamics": latest.platform_dynamics,
            "network_evolution": latest.network_evolution,
        }

    # --- Simulation meta ---
    simulation_data = {
        "simulation_id": str(sim.id),
        "name": sim.name,
        "product_description": sim.product_description,
        "target_market": sim.target_market,
        "industry": sim.industry,
        "status": sim.status.value if hasattr(sim.status, "value") else str(sim.status),
        "config": sim.config,
        "current_tick": sim.current_tick,
        "total_ticks": sim.total_ticks,
        "created_at": str(sim.created_at),
        "updated_at": str(sim.updated_at),
    }

    payload = {
        "simulation": simulation_data,
        "personas": personas_data,
        "posts": posts_data,
        "influence_events": influence_data,
        "report": report_data,
    }

    json_bytes = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="simulation_{simulation_id}.json"'
        },
    )


# ---------------------------------------------------------------------------
# Endpoint 2: Posts CSV export
# ---------------------------------------------------------------------------

@router.get(
    "/simulations/{simulation_id}/export/posts/csv",
    summary="Export posts as CSV",
    response_class=StreamingResponse,
)
async def export_posts_csv(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all posts of a simulation as a CSV file download.

    Columns: post_id, platform, author_name, is_skeptic, ingame_day, content,
             subreddit, comments_count, reactions_like, reactions_dislike,
             reactions_share
    """
    await _get_simulation_or_404(simulation_id, db)

    posts_result = await db.execute(
        select(Post)
        .where(Post.simulation_id == simulation_id)
        .options(
            selectinload(Post.author),
            selectinload(Post.comments),
            selectinload(Post.reactions),
        )
        .order_by(Post.ingame_day, Post.created_at)
    )
    posts = posts_result.scalars().all()

    fieldnames = [
        "post_id",
        "platform",
        "author_name",
        "is_skeptic",
        "ingame_day",
        "content",
        "subreddit",
        "comments_count",
        "reactions_like",
        "reactions_dislike",
        "reactions_share",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()

    for post in posts:
        reactions_like = sum(
            1 for r in post.reactions
            if (r.reaction_type.value if hasattr(r.reaction_type, "value") else str(r.reaction_type)) == "like"
        )
        reactions_dislike = sum(
            1 for r in post.reactions
            if (r.reaction_type.value if hasattr(r.reaction_type, "value") else str(r.reaction_type)) == "dislike"
        )
        reactions_share = sum(
            1 for r in post.reactions
            if (r.reaction_type.value if hasattr(r.reaction_type, "value") else str(r.reaction_type)) == "share"
        )

        writer.writerow(
            {
                "post_id": str(post.id),
                "platform": post.platform.value if hasattr(post.platform, "value") else str(post.platform),
                "author_name": post.author.name if post.author else "",
                "is_skeptic": post.author.is_skeptic if post.author else "",
                "ingame_day": post.ingame_day,
                "content": post.content,
                "subreddit": post.subreddit or "",
                "comments_count": len(post.comments),
                "reactions_like": reactions_like,
                "reactions_dislike": reactions_dislike,
                "reactions_share": reactions_share,
            }
        )

    csv_content = output.getvalue()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="posts_{simulation_id}.csv"'
        },
    )


# ---------------------------------------------------------------------------
# Endpoint 3: Personas CSV export
# ---------------------------------------------------------------------------

@router.get(
    "/simulations/{simulation_id}/export/personas/csv",
    summary="Export personas as CSV",
    response_class=StreamingResponse,
)
async def export_personas_csv(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all personas of a simulation as a CSV file download.

    Columns: persona_id, name, age, location, occupation, is_skeptic,
             initial_opinion, mood, opinion_evolution
    """
    await _get_simulation_or_404(simulation_id, db)

    personas_result = await db.execute(
        select(Persona)
        .where(Persona.simulation_id == simulation_id)
        .order_by(Persona.created_at)
    )
    personas = personas_result.scalars().all()

    fieldnames = [
        "persona_id",
        "name",
        "age",
        "location",
        "occupation",
        "is_skeptic",
        "initial_opinion",
        "mood",
        "opinion_evolution",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()

    for persona in personas:
        current_state = persona.current_state or {}
        writer.writerow(
            {
                "persona_id": str(persona.id),
                "name": persona.name,
                "age": persona.age or "",
                "location": persona.location or "",
                "occupation": persona.occupation or "",
                "is_skeptic": persona.is_skeptic,
                "initial_opinion": persona.initial_opinion or "",
                "mood": current_state.get("mood", ""),
                "opinion_evolution": current_state.get("opinion_evolution", ""),
            }
        )

    csv_content = output.getvalue()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="personas_{simulation_id}.csv"'
        },
    )
