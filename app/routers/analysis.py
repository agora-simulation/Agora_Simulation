from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AnalysisReport, Simulation
from app.schemas import AnalysisReportRead
from app.analysis.report_generator import generate_report
from app.analysis.kpi_engine import compute_kpis
from app.analysis.network_metrics import compute_network_metrics
from app.llm.resolver import resolve_for_phase

router = APIRouter()


@router.get("/{simulation_id}", response_model=AnalysisReportRead)
async def get_report(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisReportRead:
    result = await db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.simulation_id == simulation_id)
        .order_by(AnalysisReport.created_at.desc())
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Kein Report vorhanden")
    return report


@router.post("/{simulation_id}/generate", response_model=AnalysisReportRead)
async def generate_report_endpoint(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisReportRead:
    # Prüfe ob Simulation existiert
    sim_result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = sim_result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden")

    resolved = await resolve_for_phase(sim, "analysis_reports", db)
    report = await generate_report(
        simulation_id, db,
        resolved=resolved,
    )
    return report


@router.get("/{simulation_id}/kpis")
async def get_kpis(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Marktforschungs-KPIs: NPS, Brand Awareness, Engagement, Sentiment, etc."""
    sim_result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    if not sim_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden")

    return await compute_kpis(simulation_id, db)


@router.get("/{simulation_id}/network-metrics")
async def get_network_metrics(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Netzwerk-Analyse: Centrality, Communities, Graph-Statistiken."""
    sim_result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    if not sim_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden")

    return await compute_network_metrics(simulation_id, db)
