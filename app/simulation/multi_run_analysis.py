"""
Multi-Run-Analyse: Vergleicht mehrere Simulationsläufe und berechnet Konfidenz-Scores.
"""
import statistics
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Simulation, SimulationStatus, Persona, SimulationTick
from app.schemas.simulation import MultiRunComparisonResponse


async def analyze_multi_run(
    run_group_id: UUID,
    db: AsyncSession,
) -> MultiRunComparisonResponse:
    """Vergleicht alle abgeschlossenen Runs einer Gruppe.

    Berechnet:
    - Konvergenz-Konsistenz: Konvergieren alle Runs zum gleichen Ergebnis?
    - Sentiment-Bandbreite: Wie breit streuen die End-Sentiments?
    - Dimensions-Varianz: Varianz pro Meinungsdimension über alle Runs
    - Konfidenz-Scores: high/medium/low pro Dimension
    - Narrativ-Stabilität: Textuelle Einschätzung
    """
    # Alle Simulationen der Gruppe laden
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.personas))
        .where(Simulation.run_group_id == run_group_id)
        .order_by(Simulation.run_index)
    )
    simulations = result.scalars().all()

    if not simulations:
        raise ValueError(f"Keine Simulationen für run_group_id {run_group_id}")

    completed = [s for s in simulations if s.status == SimulationStatus.completed]
    run_count = len(simulations)
    completed_count = len(completed)

    if completed_count < 2:
        return MultiRunComparisonResponse(
            run_group_id=run_group_id,
            run_count=run_count,
            completed_runs=completed_count,
            convergence_consistency={"status": "insufficient_data"},
            sentiment_bandwidth={"status": "insufficient_data"},
            dimension_variance={},
            confidence_scores={},
            narrative_stability="Zu wenige abgeschlossene Runs für Vergleich (min. 2 nötig)",
            recommendation="Warten bis mehr Runs abgeschlossen sind.",
        )

    # --- 1. Dimensions-Durchschnitte pro Run sammeln ---
    dimension_keys = [
        "product_quality", "price_fairness", "brand_trust",
        "innovation", "ethical_concerns", "social_proof", "personal_relevance",
    ]

    # Pro Run: durchschnittliche Dimension-Werte
    run_dimension_avgs: list[dict[str, float]] = []
    # Pro Run: Skeptiker-Konversionsrate
    run_skeptic_conversion: list[float] = []
    # Pro Run: Polarization-Index am Ende
    run_final_polarization: list[float] = []
    # Pro Run: durchschnittlicher Gesamtscore
    run_overall_scores: list[float] = []

    for sim in completed:
        dims_by_key: dict[str, list[float]] = {k: [] for k in dimension_keys}
        skeptic_total = 0
        skeptic_converted = 0

        for persona in sim.personas:
            state = persona.current_state or {}
            opinion_dims = state.get("opinion_dimensions", {})

            for key in dimension_keys:
                val = opinion_dims.get(key)
                if val is not None:
                    dims_by_key[key].append(val)

            # Skeptiker-Konversion
            if persona.is_skeptic:
                skeptic_total += 1
                if opinion_dims:
                    avg_opinion = sum(opinion_dims.values()) / len(opinion_dims)
                    if avg_opinion > 0.1:
                        skeptic_converted += 1

        # Durchschnitte pro Dimension
        run_avgs = {}
        all_vals = []
        for key in dimension_keys:
            vals = dims_by_key[key]
            if vals:
                avg = sum(vals) / len(vals)
                run_avgs[key] = round(avg, 3)
                all_vals.extend(vals)
        run_dimension_avgs.append(run_avgs)

        if all_vals:
            run_overall_scores.append(round(sum(all_vals) / len(all_vals), 3))

        if skeptic_total > 0:
            run_skeptic_conversion.append(round(skeptic_converted / skeptic_total, 3))

        # Polarization-Index vom letzten Tick
        ticks_result = await db.execute(
            select(SimulationTick)
            .where(SimulationTick.simulation_id == sim.id)
            .order_by(SimulationTick.tick_number.desc())
            .limit(1)
        )
        last_tick = ticks_result.scalar_one_or_none()
        if last_tick and last_tick.snapshot:
            run_final_polarization.append(
                last_tick.snapshot.get("polarization_index", 0.0)
            )

    # --- 2. Varianz pro Dimension berechnen ---
    dimension_variance: dict[str, dict] = {}
    confidence_scores: dict[str, str] = {}

    for key in dimension_keys:
        values = [r.get(key, 0.0) for r in run_dimension_avgs if key in r]
        if len(values) >= 2:
            avg = sum(values) / len(values)
            stdev = statistics.stdev(values)
            var_coeff = stdev / abs(avg) if abs(avg) > 0.01 else stdev

            dimension_variance[key] = {
                "mean": round(avg, 3),
                "stdev": round(stdev, 3),
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "coefficient_of_variation": round(var_coeff, 3),
            }

            # Konfidenz-Score basierend auf Variationskoeffizient
            if var_coeff < 0.15:
                confidence_scores[key] = "high"
            elif var_coeff < 0.35:
                confidence_scores[key] = "medium"
            else:
                confidence_scores[key] = "low"
        elif len(values) == 1:
            dimension_variance[key] = {
                "mean": round(values[0], 3),
                "stdev": 0.0,
                "note": "Nur 1 Run — keine Varianz berechenbar",
            }
            confidence_scores[key] = "insufficient_data"

    # --- 3. Konvergenz-Konsistenz ---
    convergence_consistency = {}
    if run_overall_scores:
        overall_stdev = statistics.stdev(run_overall_scores) if len(run_overall_scores) >= 2 else 0.0
        convergence_consistency = {
            "overall_mean": round(sum(run_overall_scores) / len(run_overall_scores), 3),
            "overall_stdev": round(overall_stdev, 3),
            "runs_agree_on_direction": sum(
                1 for s in run_overall_scores if s > 0
            ) if run_overall_scores[0] > 0 else sum(
                1 for s in run_overall_scores if s <= 0
            ),
            "total_runs": len(run_overall_scores),
        }

    # --- 4. Sentiment-Bandbreite ---
    sentiment_bandwidth = {}
    if run_skeptic_conversion:
        sentiment_bandwidth["skeptic_conversion_rate"] = {
            "mean": round(sum(run_skeptic_conversion) / len(run_skeptic_conversion), 3),
            "min": round(min(run_skeptic_conversion), 3),
            "max": round(max(run_skeptic_conversion), 3),
            "stdev": round(
                statistics.stdev(run_skeptic_conversion), 3
            ) if len(run_skeptic_conversion) >= 2 else 0.0,
        }
    if run_final_polarization:
        sentiment_bandwidth["final_polarization"] = {
            "mean": round(sum(run_final_polarization) / len(run_final_polarization), 3),
            "min": round(min(run_final_polarization), 3),
            "max": round(max(run_final_polarization), 3),
            "stdev": round(
                statistics.stdev(run_final_polarization), 3
            ) if len(run_final_polarization) >= 2 else 0.0,
        }

    # --- 5. Narrativ-Stabilität (textuelle Einschätzung) ---
    high_conf_count = sum(1 for v in confidence_scores.values() if v == "high")
    low_conf_count = sum(1 for v in confidence_scores.values() if v == "low")
    total_dims = len(confidence_scores)

    if high_conf_count >= total_dims * 0.7:
        narrative_stability = (
            f"HOHE STABILITÄT: {high_conf_count}/{total_dims} Dimensionen zeigen konsistente "
            f"Ergebnisse über {completed_count} Runs. Die Simulation produziert belastbare Erkenntnisse."
        )
        recommendation = (
            "Die Ergebnisse sind robust. Dimensionen mit 'high' Konfidenz können als "
            "belastbare Hypothesen für echte Marktforschung verwendet werden."
        )
    elif low_conf_count >= total_dims * 0.5:
        narrative_stability = (
            f"NIEDRIGE STABILITÄT: {low_conf_count}/{total_dims} Dimensionen schwanken stark "
            f"zwischen den Runs. Die Ergebnisse sind möglicherweise Zufallsartefakte."
        )
        recommendation = (
            "Die Ergebnisse sind nicht belastbar genug für strategische Entscheidungen. "
            "Empfehlung: Simulation mit mehr Personas oder veränderten Parametern wiederholen, "
            "oder direkt echte Marktforschung durchführen."
        )
    else:
        narrative_stability = (
            f"MITTLERE STABILITÄT: Gemischte Ergebnisse — {high_conf_count} Dimensionen stabil, "
            f"{low_conf_count} instabil. Einzelne Erkenntnisse sind belastbar, andere nicht."
        )
        recommendation = (
            "Ergebnisse mit 'high' Konfidenz können als Arbeitshypothesen dienen. "
            "Dimensionen mit 'low' Konfidenz sollten mit Vorsicht behandelt werden — "
            "hier lohnt sich gezielte echte Marktforschung."
        )

    return MultiRunComparisonResponse(
        run_group_id=run_group_id,
        run_count=run_count,
        completed_runs=completed_count,
        convergence_consistency=convergence_consistency,
        sentiment_bandwidth=sentiment_bandwidth,
        dimension_variance=dimension_variance,
        confidence_scores=confidence_scores,
        narrative_stability=narrative_stability,
        recommendation=recommendation,
    )
