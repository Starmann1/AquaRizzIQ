"""AquaRizz Flood-Aware Evacuation Routing Planner (P1-16).

Calculates risk-penalized shortest paths using NetworkX Dijkstra:
  cost_e = travel_time_e * (1 + 4 * r_e)
  Edges with r_e >= 0.90 are dropped (road blocked).
  Safe Route Score (SRS) evaluated across candidate routes.
"""
from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx


class EvacuationRoutePlanner:
    """Computes flood-aware evacuation paths to designated shelters."""

    def __init__(self, base_speed_kmh: float = 35.0, flood_penalty_mult: float = 4.0):
        self.base_speed = base_speed_kmh
        self.flood_penalty = flood_penalty_mult
        self.graph = self._build_synthetic_chennai_network()

    def _build_synthetic_chennai_network(self) -> nx.Graph:
        """Construct a topological road network representing T. Nagar / Mambalam / Velachery corridor."""
        G = nx.Graph()

        # Nodes (lat, lon, name)
        nodes = {
            "N_TNAGAR_CENTER": {"pos": (80.2360, 13.0410), "name": "Panagal Park"},
            "N_USMAN_RD": {"pos": (80.2330, 13.0380), "name": "South Usman Road"},
            "N_MAMBALAM_STN": {"pos": (80.2240, 13.0360), "name": "Mambalam Railway Station"},
            "N_ANNA_SALAI": {"pos": (80.2450, 13.0330), "name": "Nandanam Anna Salai"},
            "N_VELACHERY_MAIN": {"pos": (80.2220, 12.9830), "name": "Velachery Bypass"},
            "SH_TNAGAR": {"pos": (80.2390, 13.0440), "name": "T. Nagar Relief Hall", "is_shelter": True, "safety": 0.90},
            "SH_MAMBALAM": {"pos": (80.2190, 13.0410), "name": "Mambalam Relief Camp", "is_shelter": True, "safety": 0.85},
            "SH_GURUNANAK": {"pos": (80.2190, 12.9910), "name": "Guru Nanak Shelter", "is_shelter": True, "safety": 0.88},
        }
        for n, data in nodes.items():
            G.add_node(n, **data)

        # Edges (u, v, distance_meters, base_risk, is_underpass)
        edges = [
            ("N_TNAGAR_CENTER", "SH_TNAGAR", 450, 0.15, False),
            ("N_TNAGAR_CENTER", "N_USMAN_RD", 600, 0.40, True),  # Usman Road Subway (prone to flood)
            ("N_USMAN_RD", "N_MAMBALAM_STN", 750, 0.35, False),
            ("N_MAMBALAM_STN", "SH_MAMBALAM", 500, 0.20, False),
            ("N_TNAGAR_CENTER", "N_ANNA_SALAI", 1100, 0.10, False),
            ("N_ANNA_SALAI", "N_VELACHERY_MAIN", 3200, 0.25, False),
            ("N_VELACHERY_MAIN", "SH_GURUNANAK", 900, 0.30, False),
        ]
        for u, v, dist, risk, underpass in edges:
            travel_time_s = (dist / (self.base_speed * 1000.0 / 3600.0))
            if underpass:
                travel_time_s += 120.0  # Underpass slow-down
            G.add_edge(u, v, length=dist, travel_time_s=travel_time_s, edge_risk=risk, is_underpass=underpass)

        return G

    def plan_route(
        self,
        origin_node: str,
        destination_node: str,
        hazard_risk_overlay: Dict[Tuple[str, str], float] | None = None,
    ) -> Dict[str, Any]:
        """Compute the safest route avoiding flood-inundated edges.
        
        Returns:
            Dict containing route_nodes, total_distance_m, duration_s, srs_score, status.
        """
        if origin_node not in self.graph or destination_node not in self.graph:
            return {"status": "INVALID_NODES", "message": "Origin or destination not in network"}

        # Build penalized subgraph
        H = self.graph.copy()
        hazard_overlay = hazard_risk_overlay or {}

        edges_to_remove = []
        for u, v, data in H.edges(data=True):
            # Dynamic edge risk
            edge_key = (u, v) if (u, v) in hazard_overlay else (v, u)
            effective_risk = hazard_overlay.get(edge_key, data.get("edge_risk", 0.0))

            # Block roads exceeding 0.90 risk
            if effective_risk >= 0.90:
                edges_to_remove.append((u, v))
                continue

            # Penalized travel cost
            t_base = data["travel_time_s"]
            penalized_cost = t_base * (1.0 + self.flood_penalty * effective_risk)
            H[u][v]["cost"] = penalized_cost
            H[u][v]["effective_risk"] = effective_risk

        for u, v in edges_to_remove:
            H.remove_edge(u, v)

        # Dijkstra Shortest Path
        try:
            path = nx.shortest_path(H, source=origin_node, target=destination_node, weight="cost")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return {
                "status": "NO_SAFE_ROUTE",
                "message": "All navigable paths are blocked by hazardous floodwaters.",
                "route_nodes": [],
                "distance_m": 0.0,
                "duration_s": 0.0,
                "srs_score": 0.0,
            }

        # Calculate path totals
        total_dist = 0.0
        total_time_s = 0.0
        path_risks = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            total_dist += H[u][v]["length"]
            total_time_s += H[u][v]["travel_time_s"]
            path_risks.append(H[u][v].get("effective_risk", 0.0))

        # Safe Route Score (SRS in 0-100)
        mean_risk = sum(path_risks) / max(1, len(path_risks))
        max_risk = max(path_risks) if path_risks else 0.0
        eta_minutes = total_time_s / 60.0

        tau = min(1.0, eta_minutes / 30.0)
        rho = 0.5 * mean_risk + 0.5 * max_risk
        kappa = 0.10  # Shelter risk factor
        srs = 100.0 * max(0.0, 1.0 - (0.35 * tau + 0.45 * rho + 0.20 * kappa))

        return {
            "status": "ROUTE_FOUND",
            "route_nodes": path,
            "distance_m": round(total_dist, 1),
            "duration_s": round(total_time_s, 1),
            "duration_min": round(eta_minutes, 1),
            "srs_score": round(srs, 1),
            "max_edge_risk": round(max_risk, 3),
            "mean_edge_risk": round(mean_risk, 3),
        }
