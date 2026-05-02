"""
Netzwerk-Metriken: Berechnet wissenschaftlich fundierte SNA-Metriken.

Metriken:
- Degree Centrality
- Betweenness Centrality
- Eigenvector Centrality
- Closeness Centrality
- Clustering Coefficient
- Community Detection
"""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Persona, Simulation

logger = logging.getLogger("agora.network")

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    logger.warning("networkx nicht installiert — Netzwerk-Metriken deaktiviert")


def _build_graph(personas: list[Persona]) -> "nx.Graph":
    """Erstelle einen networkx-Graph aus Persona-Verbindungen."""
    G = nx.Graph()
    persona_map = {str(p.id): p for p in personas}

    for p in personas:
        G.add_node(str(p.id), name=p.name, is_skeptic=p.is_skeptic)

    for p in personas:
        connections = p.social_connections or []
        strengths = (p.current_state or {}).get("connection_strength", {})
        for target_id in connections:
            tid = str(target_id)
            if tid in persona_map and not G.has_edge(str(p.id), tid):
                weight = strengths.get(tid, 1.0)
                if isinstance(weight, (int, float)):
                    G.add_edge(str(p.id), tid, weight=float(weight))

    return G


def _compute_centrality_metrics(G: "nx.Graph", personas: list[Persona]) -> list[dict]:
    """Berechne alle Zentralitaetsmetriken pro Node."""
    if len(G.nodes) == 0:
        return []

    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, weight="weight")
    closeness = nx.closeness_centrality(G)
    clustering = nx.clustering(G)

    # Eigenvector — kann bei disconnected Graphs fehlschlagen
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000, weight="weight")
    except nx.PowerIterationFailedConvergence:
        eigenvector = {n: 0.0 for n in G.nodes}

    persona_map = {str(p.id): p for p in personas}
    results = []

    for node_id in G.nodes:
        p = persona_map.get(node_id)
        if not p:
            continue
        results.append({
            "persona_id": node_id,
            "name": p.name,
            "is_skeptic": p.is_skeptic,
            "persona_type": p.persona_type or "individual",
            "degree_centrality": round(degree.get(node_id, 0), 4),
            "betweenness_centrality": round(betweenness.get(node_id, 0), 4),
            "eigenvector_centrality": round(eigenvector.get(node_id, 0), 4),
            "closeness_centrality": round(closeness.get(node_id, 0), 4),
            "clustering_coefficient": round(clustering.get(node_id, 0), 4),
            "connections": G.degree(node_id),
        })

    return results


def _detect_communities(G: "nx.Graph", personas: list[Persona]) -> list[dict]:
    """Einfache Community Detection via Greedy Modularity."""
    if len(G.nodes) < 3:
        return []

    try:
        communities = list(nx.community.greedy_modularity_communities(G, weight="weight"))
    except Exception:
        return []

    persona_map = {str(p.id): p for p in personas}
    result = []
    for i, community in enumerate(communities):
        members = []
        for node_id in community:
            p = persona_map.get(node_id)
            if p:
                members.append({"persona_id": node_id, "name": p.name})
        if members:
            # Compute community-internal metrics
            subgraph = G.subgraph(community)
            density = nx.density(subgraph)
            result.append({
                "community_id": i,
                "size": len(members),
                "density": round(density, 4),
                "members": members,
            })

    return result


def _compute_graph_stats(G: "nx.Graph") -> dict:
    """Globale Netzwerk-Statistiken."""
    if len(G.nodes) == 0:
        return {"nodes": 0, "edges": 0}

    stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": round(nx.density(G), 4),
        "avg_clustering": round(nx.average_clustering(G), 4),
    }

    # Connected Components
    components = list(nx.connected_components(G))
    stats["connected_components"] = len(components)
    stats["largest_component_size"] = max(len(c) for c in components) if components else 0

    # Average shortest path — nur fuer groesste Komponente
    if stats["largest_component_size"] > 1:
        largest = max(components, key=len)
        subgraph = G.subgraph(largest)
        try:
            stats["avg_shortest_path"] = round(nx.average_shortest_path_length(subgraph), 3)
        except Exception:
            stats["avg_shortest_path"] = None
    else:
        stats["avg_shortest_path"] = None

    # Degree distribution
    degrees = [d for _, d in G.degree()]
    stats["avg_degree"] = round(sum(degrees) / len(degrees), 2) if degrees else 0
    stats["max_degree"] = max(degrees) if degrees else 0

    return stats


async def compute_network_metrics(simulation_id: UUID, db: AsyncSession) -> dict:
    """Berechne alle Netzwerk-Metriken fuer eine Simulation."""
    if not HAS_NETWORKX:
        return {"error": "networkx nicht installiert. Bitte `pip install networkx` ausfuehren."}

    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.personas))
        .where(Simulation.id == simulation_id)
    )
    sim = sim_result.scalar_one_or_none()
    if not sim:
        return {"error": "Simulation nicht gefunden"}

    personas = sim.personas
    if not personas:
        return {"error": "Keine Personas vorhanden"}

    G = _build_graph(personas)
    centrality = _compute_centrality_metrics(G, personas)
    communities = _detect_communities(G, personas)
    graph_stats = _compute_graph_stats(G)

    # Rankings
    top_degree = sorted(centrality, key=lambda x: x["degree_centrality"], reverse=True)[:10]
    top_betweenness = sorted(centrality, key=lambda x: x["betweenness_centrality"], reverse=True)[:10]
    top_eigenvector = sorted(centrality, key=lambda x: x["eigenvector_centrality"], reverse=True)[:10]
    top_closeness = sorted(centrality, key=lambda x: x["closeness_centrality"], reverse=True)[:10]

    return {
        "simulation_id": str(simulation_id),
        "graph_stats": graph_stats,
        "centrality": centrality,
        "communities": communities,
        "rankings": {
            "top_degree": top_degree,
            "top_betweenness": top_betweenness,
            "top_eigenvector": top_eigenvector,
            "top_closeness": top_closeness,
        },
    }
