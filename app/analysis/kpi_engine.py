"""
KPI-Engine: Berechnet Marktforschungs-Standard-KPIs aus Simulationsdaten.

KPIs:
- Simulated NPS (Net Promoter Score)
- Brand Awareness
- Share of Voice
- Engagement Rate
- Adoption Rate
- Virality Coefficient
- Sentiment Score
- Churn Risk
"""
import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    InfluenceEvent,
    Persona,
    Post,
    Comment,
    Reaction,
    Simulation,
    SimulationTick,
)

logger = logging.getLogger("simulator.kpi")


def _opinion_to_nps_category(opinion_dims: dict) -> str:
    """Mappe Opinion-Dimensionen auf NPS-Kategorie (Promoter/Passive/Detractor)."""
    if not opinion_dims:
        return "passive"
    # Gewichteter Score aus quality + trust + relevance (die kaufrelevantesten Dimensionen)
    weights = {
        "product_quality": 0.3,
        "brand_trust": 0.3,
        "personal_relevance": 0.2,
        "price_fairness": 0.2,
    }
    score = 0.0
    total_weight = 0.0
    for key, weight in weights.items():
        if key in opinion_dims:
            score += opinion_dims[key] * weight
            total_weight += weight
    if total_weight == 0:
        return "passive"
    normalized = score / total_weight  # -1.0 bis +1.0
    if normalized > 0.3:
        return "promoter"
    elif normalized < -0.2:
        return "detractor"
    return "passive"


def _compute_nps(personas: list[Persona]) -> dict:
    """Berechne simulierten NPS aus Persona-Opinion-Dimensionen."""
    promoters = 0
    passives = 0
    detractors = 0

    for p in personas:
        state = p.current_state or {}
        dims = state.get("opinion_dimensions", {})
        cat = _opinion_to_nps_category(dims)
        if cat == "promoter":
            promoters += 1
        elif cat == "detractor":
            detractors += 1
        else:
            passives += 1

    total = len(personas) or 1
    nps = round(((promoters - detractors) / total) * 100, 1)
    return {
        "score": nps,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
        "promoter_pct": round(promoters / total * 100, 1),
        "detractor_pct": round(detractors / total * 100, 1),
    }


def _compute_brand_awareness(personas: list[Persona], author_ids: set[str]) -> dict:
    """Anteil Personas die mind. 1x gepostet oder kommentiert haben."""
    total = len(personas) or 1
    aware = sum(1 for p in personas if str(p.id) in author_ids)
    return {
        "aware_count": aware,
        "total": len(personas),
        "awareness_pct": round(aware / total * 100, 1),
    }


def _compute_sov_per_tick(posts: list[Post], total_ticks: int) -> list[dict]:
    """Share of Voice pro Tick — Anteil produktbezogener Posts an Gesamt-Posts."""
    # In unserer Simulation sind alle Posts produktbezogen, daher SOV = Posts/Tick
    by_day: dict[int, int] = {}
    for post in posts:
        by_day[post.ingame_day] = by_day.get(post.ingame_day, 0) + 1

    result = []
    for day in range(1, total_ticks + 1):
        count = by_day.get(day, 0)
        result.append({"day": day, "post_count": count})
    return result


def _compute_engagement_rate(
    posts: list[Post],
    comment_counts: dict[str, int],
    reaction_counts: dict[str, int],
    total_ticks: int,
) -> list[dict]:
    """Engagement Rate pro Tick: (Reactions + Comments) / Posts."""
    posts_by_day: dict[int, list] = {}
    for post in posts:
        posts_by_day.setdefault(post.ingame_day, []).append(post)

    result = []
    for day in range(1, total_ticks + 1):
        day_posts = posts_by_day.get(day, [])
        if not day_posts:
            result.append({"day": day, "rate": 0, "posts": 0, "interactions": 0})
            continue
        interactions = 0
        for post in day_posts:
            pid = str(post.id)
            interactions += comment_counts.get(pid, 0) + reaction_counts.get(pid, 0)
        rate = round(interactions / len(day_posts), 2) if day_posts else 0
        result.append({
            "day": day,
            "rate": rate,
            "posts": len(day_posts),
            "interactions": interactions,
        })
    return result


def _compute_adoption_rate(personas: list[Persona], total_ticks: int) -> list[dict]:
    """Adoption Rate: Anteil Personas mit positivem Opinion-Shift ueber Zeit.

    Wir approximieren dies aus dem aktuellen Endzustand (da wir keine Tick-History
    pro Persona haben), berechnen aber den Gesamtwert.
    """
    total = len(personas) or 1
    adopted = 0
    for p in personas:
        state = p.current_state or {}
        dims = state.get("opinion_dimensions", {})
        if dims:
            avg = sum(dims.values()) / len(dims)
            if avg > 0.1:
                adopted += 1
    return {
        "adopted_count": adopted,
        "total": total,
        "adoption_pct": round(adopted / total * 100, 1),
    }


def _compute_virality(posts: list[Post], comment_counts: dict[str, int], reaction_counts: dict[str, int]) -> dict:
    """Virality Coefficient: Durchschnittliche Sekundaer-Interaktionen pro Post."""
    if not posts:
        return {"coefficient": 0, "avg_comments": 0, "avg_reactions": 0}

    total_comments = sum(comment_counts.values())
    total_reactions = sum(reaction_counts.values())
    n = len(posts)
    return {
        "coefficient": round((total_comments + total_reactions) / n, 2),
        "avg_comments": round(total_comments / n, 2),
        "avg_reactions": round(total_reactions / n, 2),
        "total_posts": n,
    }


def _compute_sentiment_score(personas: list[Persona], total_ticks: int) -> dict:
    """Gewichteter Sentiment-Score ueber alle Opinion-Dimensionen."""
    all_scores = []
    for p in personas:
        state = p.current_state or {}
        dims = state.get("opinion_dimensions", {})
        if dims:
            avg = sum(dims.values()) / len(dims)
            all_scores.append(avg)

    if not all_scores:
        return {"overall": 0, "min": 0, "max": 0, "positive_pct": 0, "negative_pct": 0, "neutral_pct": 100}

    positive = sum(1 for s in all_scores if s > 0.1)
    negative = sum(1 for s in all_scores if s < -0.1)
    neutral = len(all_scores) - positive - negative
    n = len(all_scores)

    return {
        "overall": round(sum(all_scores) / n, 3),
        "min": round(min(all_scores), 3),
        "max": round(max(all_scores), 3),
        "positive_pct": round(positive / n * 100, 1),
        "negative_pct": round(negative / n * 100, 1),
        "neutral_pct": round(neutral / n * 100, 1),
    }


def _compute_churn_risk(personas: list[Persona]) -> dict:
    """Personas mit negativem Sentiment = Churn Risk.

    Abgestufte Bewertung:
    - high_risk: avg < -0.2 ODER mind. 3 Dimensionen negativ (<-0.1)
    - medium_risk: avg < 0 UND mind. 2 Dimensionen negativ
    """
    high_risk = []
    medium_risk = []

    for p in personas:
        state = p.current_state or {}
        dims = state.get("opinion_dimensions", {})
        if not dims:
            continue
        avg = sum(dims.values()) / len(dims)
        negative_dims = [k for k, v in dims.items() if v < -0.1]
        worst_dim = min(dims, key=dims.get) if dims else None
        worst_val = round(min(dims.values()), 3) if dims else None

        entry = {
            "persona_id": str(p.id),
            "name": p.name,
            "avg_opinion": round(avg, 3),
            "is_skeptic": p.is_skeptic,
            "negative_dimensions": negative_dims,
            "worst_dimension": worst_dim,
            "worst_value": worst_val,
        }

        if avg < -0.2 or len(negative_dims) >= 3:
            entry["risk_level"] = "high"
            high_risk.append(entry)
        elif avg < 0 and len(negative_dims) >= 2:
            entry["risk_level"] = "medium"
            medium_risk.append(entry)

    total = len(personas) or 1
    all_at_risk = high_risk + medium_risk
    all_at_risk.sort(key=lambda x: x["avg_opinion"])

    return {
        "at_risk_count": len(all_at_risk),
        "at_risk_pct": round(len(all_at_risk) / total * 100, 1),
        "high_risk_count": len(high_risk),
        "medium_risk_count": len(medium_risk),
        "personas": all_at_risk[:20],
    }


def _compute_dimension_breakdown(personas: list[Persona]) -> dict:
    """Aufschluesselung pro Opinion-Dimension ueber alle Personas."""
    all_dims: dict[str, list[float]] = {}
    for p in personas:
        state = p.current_state or {}
        dims = state.get("opinion_dimensions", {})
        for key, val in dims.items():
            all_dims.setdefault(key, []).append(val)

    result = {}
    for key, values in all_dims.items():
        n = len(values)
        positive = sum(1 for v in values if v > 0.1)
        negative = sum(1 for v in values if v < -0.1)
        result[key] = {
            "avg": round(sum(values) / n, 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "std": round((sum((v - sum(values) / n) ** 2 for v in values) / n) ** 0.5, 3),
            "positive_pct": round(positive / n * 100, 1),
            "negative_pct": round(negative / n * 100, 1),
        }
    return result


async def compute_kpis(simulation_id: UUID, db: AsyncSession) -> dict:
    """Berechne alle KPIs fuer eine Simulation."""

    # Simulation mit Personas laden
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.personas))
        .where(Simulation.id == simulation_id)
    )
    sim = sim_result.scalar_one_or_none()
    if not sim:
        return {"error": "Simulation nicht gefunden"}

    personas = sim.personas
    total_ticks = sim.current_tick or sim.total_ticks

    # Posts laden
    posts_result = await db.execute(
        select(Post).where(Post.simulation_id == simulation_id)
    )
    posts = list(posts_result.scalars().all())

    # Comment-Counts pro Post
    comment_result = await db.execute(
        select(Comment.post_id, func.count(Comment.id))
        .join(Post, Comment.post_id == Post.id)
        .where(Post.simulation_id == simulation_id)
        .group_by(Comment.post_id)
    )
    comment_counts = {str(row[0]): row[1] for row in comment_result}

    # Reaction-Counts pro Post
    reaction_result = await db.execute(
        select(Reaction.post_id, func.count(Reaction.id))
        .join(Post, Reaction.post_id == Post.id)
        .where(Post.simulation_id == simulation_id)
        .group_by(Reaction.post_id)
    )
    reaction_counts = {str(row[0]): row[1] for row in reaction_result}

    # Author-IDs (Posts + Comments)
    post_author_ids = {str(p.author_id) for p in posts}
    comment_author_result = await db.execute(
        select(Comment.author_id)
        .join(Post, Comment.post_id == Post.id)
        .where(Post.simulation_id == simulation_id)
        .distinct()
    )
    comment_author_ids = {str(row[0]) for row in comment_author_result}
    all_author_ids = post_author_ids | comment_author_ids

    # Influence Events Count
    influence_count_result = await db.execute(
        select(func.count(InfluenceEvent.id))
        .where(InfluenceEvent.simulation_id == simulation_id)
    )
    influence_count = influence_count_result.scalar_one()

    # KPIs berechnen
    nps = _compute_nps(personas)
    awareness = _compute_brand_awareness(personas, all_author_ids)
    sov = _compute_sov_per_tick(posts, total_ticks)
    engagement = _compute_engagement_rate(posts, comment_counts, reaction_counts, total_ticks)
    adoption = _compute_adoption_rate(personas, total_ticks)
    virality = _compute_virality(posts, comment_counts, reaction_counts)
    sentiment = _compute_sentiment_score(personas, total_ticks)
    churn = _compute_churn_risk(personas)
    dimensions = _compute_dimension_breakdown(personas)

    return {
        "simulation_id": str(simulation_id),
        "total_personas": len(personas),
        "total_posts": len(posts),
        "total_ticks": total_ticks,
        "total_influence_events": influence_count,
        "nps": nps,
        "brand_awareness": awareness,
        "share_of_voice": sov,
        "engagement_rate": engagement,
        "adoption": adoption,
        "virality": virality,
        "sentiment": sentiment,
        "churn_risk": churn,
        "dimension_breakdown": dimensions,
    }
