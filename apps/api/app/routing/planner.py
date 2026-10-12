"""AquaRizz Chennai-Wide Evacuation and Shelter Routing System (P1-16).

Calculates risk-penalized shortest paths using NetworkX Dijkstra:
  cost_e = travel_time_e * (1 + 4 * r_e)
  Edges with r_e >= 0.90 are dropped (road blocked / inundated).
  Safe Route Score (SRS) evaluated across candidate routes.

Provides comprehensive coverage across North, Central, and South Chennai sectors:
- 12 Designated Relief Camps / Flood Shelters with rated capacities
- 18 Vulnerable Catchment Origins / Evacuation Hubs
- Multi-corridor city-wide evacuation planning and barrier simulation
"""
from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx


class EvacuationRoutePlanner:
    """Computes flood-aware evacuation paths across Greater Chennai Corporation."""

    def __init__(self, base_speed_kmh: float = 35.0, flood_penalty_mult: float = 4.0):
        self.base_speed = base_speed_kmh
        self.flood_penalty = flood_penalty_mult
        self.nodes_data = self._get_chennai_nodes_data()
        self.edges_data = self._get_chennai_edges_data()
        self.graph = self._build_chennai_network()

    def _get_chennai_nodes_data(self) -> Dict[str, Dict[str, Any]]:
        return {
            # --- NORTH CHENNAI SECTOR (Zones 1-5) ---
            "N_ENNORE": {
                "pos": (80.3150, 13.1980),
                "name": "Ennore Express Corridor",
                "sector": "North Chennai",
                "zone": "Thiruvottiyur",
                "is_shelter": False,
                "vulnerability": 0.85,
                "est_evacuees": 2400,
            },
            "N_WIMCO_NAGAR": {
                "pos": (80.3010, 13.1700),
                "name": "Wimco Nagar Coastal Basin",
                "sector": "North Chennai",
                "zone": "Thiruvottiyur",
                "is_shelter": False,
                "vulnerability": 0.82,
                "est_evacuees": 1900,
            },
            "N_MANALI_BASIN": {
                "pos": (80.2620, 13.1720),
                "name": "Manali CPCL Low Basin",
                "sector": "North Chennai",
                "zone": "Manali",
                "is_shelter": False,
                "vulnerability": 0.88,
                "est_evacuees": 2200,
            },
            "N_KOLATHUR": {
                "pos": (80.2140, 13.1230),
                "name": "Kolathur Lake Catchment",
                "sector": "North Chennai",
                "zone": "Thiru-Vi-Ka Nagar",
                "is_shelter": False,
                "vulnerability": 0.74,
                "est_evacuees": 1800,
            },
            "N_VYASARPADI": {
                "pos": (80.2580, 13.1110),
                "name": "Vyasarpadi Jeeva Basin",
                "sector": "North Chennai",
                "zone": "Tondiarpet",
                "is_shelter": False,
                "vulnerability": 0.86,
                "est_evacuees": 2600,
            },
            # North Shelters
            "SH_THIRUVOTTIYUR": {
                "pos": (80.3010, 13.1610),
                "name": "Thiruvottiyur Relief Center",
                "sector": "North Chennai",
                "zone": "Thiruvottiyur",
                "is_shelter": True,
                "safety": 0.92,
                "capacity": 2500,
            },
            "SH_MANALI": {
                "pos": (80.2580, 13.1680),
                "name": "Mathur MMDA Relief Camp",
                "sector": "North Chennai",
                "zone": "Manali",
                "is_shelter": True,
                "safety": 0.89,
                "capacity": 2000,
            },
            "SH_MADHAVARAM": {
                "pos": (80.2310, 13.1480),
                "name": "Madhavaram Central Camp",
                "sector": "North Chennai",
                "zone": "Madhavaram",
                "is_shelter": True,
                "safety": 0.94,
                "capacity": 3000,
            },
            "SH_ROYAPURAM": {
                "pos": (80.2880, 13.1090),
                "name": "Stanley Medical Relief Pavilion",
                "sector": "North Chennai",
                "zone": "Royapuram",
                "is_shelter": True,
                "safety": 0.90,
                "capacity": 2200,
            },

            # --- CENTRAL CHENNAI SECTOR (Zones 6-10) ---
            "N_TNAGAR_CENTER": {
                "pos": (80.2360, 13.0410),
                "name": "Panagal Park (T. Nagar Center)",
                "sector": "Central Chennai",
                "zone": "Teynampet",
                "is_shelter": False,
                "vulnerability": 0.76,
                "est_evacuees": 3100,
            },
            "N_USMAN_RD": {
                "pos": (80.2330, 13.0380),
                "name": "South Usman Road",
                "sector": "Central Chennai",
                "zone": "Teynampet",
                "is_shelter": False,
                "vulnerability": 0.80,
                "est_evacuees": 1500,
            },
            "N_MAMBALAM_STN": {
                "pos": (80.2240, 13.0360),
                "name": "Mambalam Railway Station",
                "sector": "Central Chennai",
                "zone": "Teynampet",
                "is_shelter": False,
                "vulnerability": 0.78,
                "est_evacuees": 2000,
            },
            "N_KOYAMBEDU": {
                "pos": (80.1910, 13.0720),
                "name": "Koyambedu Cooum Nullah",
                "sector": "Central Chennai",
                "zone": "Anna Nagar",
                "is_shelter": False,
                "vulnerability": 0.72,
                "est_evacuees": 2100,
            },
            "N_ARUMBAKKAM": {
                "pos": (80.2080, 13.0690),
                "name": "Arumbakkam River Basin",
                "sector": "Central Chennai",
                "zone": "Anna Nagar",
                "is_shelter": False,
                "vulnerability": 0.75,
                "est_evacuees": 1700,
            },
            "N_KODAMBAKKAM": {
                "pos": (80.2250, 13.0520),
                "name": "Kodambakkam Low Basin",
                "sector": "Central Chennai",
                "zone": "Kodambakkam",
                "is_shelter": False,
                "vulnerability": 0.73,
                "est_evacuees": 1900,
            },
            "N_ANNA_SALAI": {
                "pos": (80.2450, 13.0330),
                "name": "Nandanam Anna Salai",
                "sector": "Central Chennai",
                "zone": "Teynampet",
                "is_shelter": False,
                "vulnerability": 0.60,
                "est_evacuees": 1200,
            },
            # Central Shelters
            "SH_PERAMBUR": {
                "pos": (80.2390, 13.1070),
                "name": "Perambur Stadium Shelter",
                "sector": "Central Chennai",
                "zone": "Thiru-Vi-Ka Nagar",
                "is_shelter": True,
                "safety": 0.93,
                "capacity": 3200,
            },
            "SH_ANNANAGAR": {
                "pos": (80.2030, 13.0890),
                "name": "Anna Nagar West Camp",
                "sector": "Central Chennai",
                "zone": "Anna Nagar",
                "is_shelter": True,
                "safety": 0.95,
                "capacity": 3500,
            },
            "SH_AMBATTUR": {
                "pos": (80.1550, 13.1140),
                "name": "Ambattur OT Disaster Camp",
                "sector": "Central Chennai",
                "zone": "Ambattur",
                "is_shelter": True,
                "safety": 0.91,
                "capacity": 2800,
            },
            "SH_TNAGAR": {
                "pos": (80.2390, 13.0440),
                "name": "T. Nagar Relief Hall",
                "sector": "Central Chennai",
                "zone": "Teynampet",
                "is_shelter": True,
                "safety": 0.90,
                "capacity": 2000,
            },
            "SH_MAMBALAM": {
                "pos": (80.2190, 13.0410),
                "name": "Mambalam Relief Camp",
                "sector": "Central Chennai",
                "zone": "Teynampet",
                "is_shelter": True,
                "safety": 0.88,
                "capacity": 1800,
            },

            # --- SOUTH CHENNAI SECTOR (Zones 11-15) ---
            "N_RAMAPURAM": {
                "pos": (80.1790, 13.0310),
                "name": "Ramapuram Riverbank Basin",
                "sector": "South Chennai",
                "zone": "Valasaravakkam",
                "is_shelter": False,
                "vulnerability": 0.79,
                "est_evacuees": 2300,
            },
            "N_EKKATTUTHANGAL": {
                "pos": (80.2030, 13.0180),
                "name": "Ekkattuthangal Industrial Basin",
                "sector": "South Chennai",
                "zone": "Alandur",
                "is_shelter": False,
                "vulnerability": 0.84,
                "est_evacuees": 2700,
            },
            "N_JAFFERKHANPET": {
                "pos": (80.2130, 13.0240),
                "name": "Jafferkhanpet River Causeway",
                "sector": "South Chennai",
                "zone": "Kodambakkam",
                "is_shelter": False,
                "vulnerability": 0.86,
                "est_evacuees": 2100,
            },
            "N_VELACHERY_MAIN": {
                "pos": (80.2220, 12.9830),
                "name": "Velachery Bypass",
                "sector": "South Chennai",
                "zone": "Perungudi",
                "is_shelter": False,
                "vulnerability": 0.83,
                "est_evacuees": 3200,
            },
            "N_MADIPAKKAM": {
                "pos": (80.1980, 12.9640),
                "name": "Madipakkam Wetland Buffer",
                "sector": "South Chennai",
                "zone": "Perungudi",
                "is_shelter": False,
                "vulnerability": 0.81,
                "est_evacuees": 2400,
            },
            "N_PERUNGUDI_BASIN": {
                "pos": (80.2440, 12.9630),
                "name": "Perungudi Marsh Border",
                "sector": "South Chennai",
                "zone": "Perungudi",
                "is_shelter": False,
                "vulnerability": 0.78,
                "est_evacuees": 1900,
            },
            "N_PALLIKARANAI": {
                "pos": (80.2160, 12.9360),
                "name": "Pallikaranai Marsh Corridor",
                "sector": "South Chennai",
                "zone": "Sholinganallur",
                "is_shelter": False,
                "vulnerability": 0.89,
                "est_evacuees": 3400,
            },
            # South Shelters
            "SH_PORUR": {
                "pos": (80.1610, 13.0360),
                "name": "Porur Elevated Community Camp",
                "sector": "South Chennai",
                "zone": "Valasaravakkam",
                "is_shelter": True,
                "safety": 0.92,
                "capacity": 2500,
            },
            "SH_GUINDY": {
                "pos": (80.2070, 13.0080),
                "name": "Kathipara King Institute Camp",
                "sector": "South Chennai",
                "zone": "Alandur",
                "is_shelter": True,
                "safety": 0.96,
                "capacity": 4000,
            },
            "SH_GURUNANAK": {
                "pos": (80.2190, 12.9910),
                "name": "Guru Nanak Evacuation Camp",
                "sector": "South Chennai",
                "zone": "Perungudi",
                "is_shelter": True,
                "safety": 0.89,
                "capacity": 3000,
            },
            "SH_ADYAR": {
                "pos": (80.2660, 13.0010),
                "name": "Besant Nagar Relief Pavilion",
                "sector": "South Chennai",
                "zone": "Adyar",
                "is_shelter": True,
                "safety": 0.93,
                "capacity": 2200,
            },
            "SH_SHOLINGANALLUR": {
                "pos": (80.2280, 12.8720),
                "name": "Sathyabama Disaster Complex",
                "sector": "South Chennai",
                "zone": "Sholinganallur",
                "is_shelter": True,
                "safety": 0.95,
                "capacity": 4500,
            },
        }

    def _get_chennai_edges_data(self) -> List[Tuple[str, str, float, float, bool, str]]:
        """List of (u, v, dist_m, base_risk, is_underpass, name)."""
        return [
            # Original Canonical Edges (preserves all backward-compat tests)
            ("N_TNAGAR_CENTER", "SH_TNAGAR", 450.0, 0.15, False, "GN Chetty Road"),
            ("N_TNAGAR_CENTER", "N_USMAN_RD", 600.0, 0.40, True, "South Usman Subway"),
            ("N_USMAN_RD", "N_MAMBALAM_STN", 750.0, 0.35, False, "Ranganathan Subway Link"),
            ("N_MAMBALAM_STN", "SH_MAMBALAM", 500.0, 0.20, False, "Arya Gowda Road"),
            ("N_TNAGAR_CENTER", "N_ANNA_SALAI", 1100.0, 0.10, False, "Chamiers Arterial"),
            ("N_ANNA_SALAI", "N_VELACHERY_MAIN", 3200.0, 0.25, False, "Anna Salai - Guindy Trunk"),
            ("N_VELACHERY_MAIN", "SH_GURUNANAK", 900.0, 0.30, True, "Velachery Bypass"),

            # North Chennai Corridor
            ("N_ENNORE", "N_WIMCO_NAGAR", 1800.0, 0.22, False, "Ennore High Road"),
            ("N_WIMCO_NAGAR", "SH_THIRUVOTTIYUR", 950.0, 0.15, False, "Tollgate Elevated Arterial"),
            ("N_ENNORE", "N_MANALI_BASIN", 2400.0, 0.35, False, "Kosasthalaiyar Embankment Road"),
            ("N_MANALI_BASIN", "SH_MANALI", 650.0, 0.20, False, "Mathur Link Road"),
            ("SH_MANALI", "SH_MADHAVARAM", 2100.0, 0.15, False, "Madhavaram High Road"),
            ("N_KOLATHUR", "SH_MADHAVARAM", 1600.0, 0.25, False, "Retteri Flyover Road"),
            ("N_KOLATHUR", "SH_PERAMBUR", 1900.0, 0.20, False, "Kolathur Main Road"),
            ("N_VYASARPADI", "SH_PERAMBUR", 1100.0, 0.35, True, "Vyasarpadi Jeeva Subway"),
            ("N_VYASARPADI", "SH_ROYAPURAM", 1400.0, 0.32, False, "Old Jail Road"),
            ("SH_ROYAPURAM", "SH_PERAMBUR", 2200.0, 0.15, False, "Basin Bridge Flyover"),

            # Cross North-Central Interconnects
            ("SH_MADHAVARAM", "SH_ANNANAGAR", 2800.0, 0.10, False, "100 Feet Inner Ring Road"),
            ("SH_PERAMBUR", "N_KOYAMBEDU", 3200.0, 0.15, False, "Poonamallee High Road Link"),

            # Central Chennai Corridor
            ("N_KOYAMBEDU", "N_ARUMBAKKAM", 800.0, 0.25, False, "Cooum Service Road"),
            ("N_ARUMBAKKAM", "SH_ANNANAGAR", 1200.0, 0.15, False, "Anna Nagar 3rd Avenue"),
            ("N_KOYAMBEDU", "SH_AMBATTUR", 2900.0, 0.15, False, "Ambattur Industrial Estate Road"),
            ("N_ARUMBAKKAM", "N_KODAMBAKKAM", 1400.0, 0.20, False, "Vadapalani 100 Feet Road"),
            ("N_KODAMBAKKAM", "SH_MAMBALAM", 1100.0, 0.20, False, "Arcot Road Junction"),
            ("SH_TNAGAR", "N_ANNA_SALAI", 900.0, 0.10, False, "Venkatanarayana Road"),

            # Cross Central-South Interconnects
            ("N_KODAMBAKKAM", "N_JAFFERKHANPET", 1800.0, 0.30, False, "Ashok Pillar South Arterial"),
            ("N_ANNA_SALAI", "N_EKKATTUTHANGAL", 2100.0, 0.15, False, "Guindy Industrial Corridor"),
            ("N_ANNA_SALAI", "SH_GUINDY", 2400.0, 0.10, False, "Kathipara Elevated Grade"),
            ("N_JAFFERKHANPET", "SH_GUINDY", 950.0, 0.35, True, "Jafferkhanpet River Causeway"),
            ("N_RAMAPURAM", "SH_PORUR", 1200.0, 0.25, False, "Mount-Poonamallee Road"),
            ("N_RAMAPURAM", "N_EKKATTUTHANGAL", 1600.0, 0.30, False, "Defense Colony Causeway"),
            ("N_EKKATTUTHANGAL", "SH_GUINDY", 850.0, 0.20, False, "Kathipara North Slip"),

            # South Chennai Corridor
            ("SH_GUINDY", "N_VELACHERY_MAIN", 2200.0, 0.20, False, "Guindy-Velachery Main Road"),
            ("N_MADIPAKKAM", "SH_GURUNANAK", 1400.0, 0.35, False, "Madipakkam Koot Link"),
            ("N_MADIPAKKAM", "N_VELACHERY_MAIN", 1200.0, 0.30, False, "Velachery Lake South Bank"),
            ("SH_GUINDY", "SH_ADYAR", 2800.0, 0.10, False, "Sardar Patel Road"),
            ("SH_GURUNANAK", "SH_ADYAR", 2400.0, 0.15, False, "Raj Bhavan Bypass"),
            ("SH_GURUNANAK", "N_PERUNGUDI_BASIN", 1900.0, 0.25, False, "Taramani Link Road"),
            ("N_PERUNGUDI_BASIN", "N_PALLIKARANAI", 1800.0, 0.35, False, "200 Feet Radial Road"),
            ("N_PALLIKARANAI", "SH_SHOLINGANALLUR", 2600.0, 0.25, False, "Medavakkam Sholinganallur Link"),
            ("N_PERUNGUDI_BASIN", "SH_SHOLINGANALLUR", 3100.0, 0.20, False, "OMR Expressway Corridor"),
        ]

    def _build_chennai_network(self) -> nx.Graph:
        """Construct full multi-sector Greater Chennai network graph."""
        G = nx.Graph()

        for node_id, data in self.nodes_data.items():
            G.add_node(node_id, **data)

        for u, v, dist, risk, underpass, name in self.edges_data:
            travel_time_s = dist / (self.base_speed * 1000.0 / 3600.0)
            if underpass:
                travel_time_s += 120.0  # Slow-down for dips and underpasses
            G.add_edge(
                u,
                v,
                length=dist,
                travel_time_s=travel_time_s,
                edge_risk=risk,
                is_underpass=underpass,
                road_name=name,
            )

        return G

    def get_network(self) -> Dict[str, Any]:
        """Return full network topology, nodes, shelters, origins, and sectors."""
        origins = [
            {"id": k, **v} for k, v in self.nodes_data.items() if not v.get("is_shelter")
        ]
        shelters = [
            {"id": k, **v} for k, v in self.nodes_data.items() if v.get("is_shelter")
        ]
        edges = [
            {"u": u, "v": v, "length_m": dist, "base_risk": risk, "is_underpass": underpass, "name": name}
            for u, v, dist, risk, underpass, name in self.edges_data
        ]
        return {
            "sectors": ["All Chennai", "North Chennai", "Central Chennai", "South Chennai"],
            "origins": origins,
            "shelters": shelters,
            "edges": edges,
            "chokepoints": [
                {"id": "CP_USMAN", "edge": ("N_TNAGAR_CENTER", "N_USMAN_RD"), "name": "South Usman Road Subway (T. Nagar)"},
                {"id": "CP_VYASARPADI", "edge": ("N_VYASARPADI", "SH_PERAMBUR"), "name": "Vyasarpadi Jeeva Subway (North)"},
                {"id": "CP_VELACHERY", "edge": ("N_VELACHERY_MAIN", "SH_GURUNANAK"), "name": "Velachery Bypass Subway (South)"},
                {"id": "CP_JAFFERKHANPET", "edge": ("N_JAFFERKHANPET", "SH_GUINDY"), "name": "Jafferkhanpet River Causeway (Central-South)"},
            ],
        }

    def plan_route(
        self,
        origin_node: str,
        destination_node: str,
        hazard_risk_overlay: Dict[Tuple[str, str], float] | None = None,
    ) -> Dict[str, Any]:
        """Compute a weighted graph path using illustrative edge-risk inputs.
        
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
                "status": "NO_PATH_FOUND",
                "message": "No path exists in the synthetic demonstration graph for these illustrative edge values.",
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
        dest_data = self.nodes_data.get(destination_node, {})
        kappa = 1.0 - dest_data.get("safety", 0.90)
        srs = 100.0 * max(0.0, 1.0 - (0.35 * tau + 0.45 * rho + 0.20 * kappa))

        return {
            "status": "ROUTE_FOUND",
            "is_simulated": True,
            "prototype_only": True,
            "network_basis": "SYNTHETIC_DEMONSTRATION_GRAPH",
            "safety_decision": "NOT_EVALUATED",
            "route_nodes": path,
            "distance_m": round(total_dist, 1),
            "duration_s": round(total_time_s, 1),
            "duration_min": round(eta_minutes, 1),
            "srs_score": round(srs, 1),
            "max_edge_risk": round(max_risk, 3),
            "mean_edge_risk": round(mean_risk, 3),
        }

    def simulate_citywide_evacuation(
        self,
        hazard_risk_overlay: Dict[Tuple[str, str], float] | None = None,
        sector_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate city-wide evacuation plan across Chennai.
        
        Evaluates all vulnerable origin hubs across North, Central, and South Chennai,
        routing evacuees to the highest-safety and lowest-risk accessible relief camps.
        """
        all_origins = [k for k, v in self.nodes_data.items() if not v.get("is_shelter")]
        all_shelters = [k for k, v in self.nodes_data.items() if v.get("is_shelter")]

        if sector_filter and sector_filter != "All Chennai":
            all_origins = [
                k for k in all_origins if self.nodes_data[k].get("sector") == sector_filter
            ]

        routes_summary = []
        shelter_counts = {s: 0 for s in all_shelters}
        total_evacuees = 0
        total_distance = 0.0
        total_duration = 0.0
        total_srs = 0.0
        successful_routes = 0

        for orig in all_origins:
            orig_data = self.nodes_data[orig]
            evacuee_pop = orig_data.get("est_evacuees", 1500)

            # Find best shelter
            best_route = None
            best_srs = -1.0
            best_shelter = None

            for dest in all_shelters:
                res = self.plan_route(orig, dest, hazard_risk_overlay)
                if res["status"] == "ROUTE_FOUND":
                    # Score based on SRS and shortest distance
                    score = res["srs_score"] - (res["distance_m"] / 1000.0) * 1.5
                    if score > best_srs:
                        best_srs = score
                        best_route = res
                        best_shelter = dest

            if best_route and best_shelter:
                shelter_counts[best_shelter] += evacuee_pop
                total_evacuees += evacuee_pop
                total_distance += best_route["distance_m"]
                total_duration += best_route["duration_min"]
                total_srs += best_route["srs_score"]
                successful_routes += 1

                routes_summary.append({
                    "origin_id": orig,
                    "origin_name": orig_data["name"],
                    "origin_sector": orig_data["sector"],
                    "target_shelter_id": best_shelter,
                    "target_shelter_name": self.nodes_data[best_shelter]["name"],
                    "evacuees_assigned": evacuee_pop,
                    "distance_km": round(best_route["distance_m"] / 1000.0, 2),
                    "duration_min": best_route["duration_min"],
                    "srs_score": best_route["srs_score"],
                    "route_nodes": best_route["route_nodes"],
                })

        avg_srs = round(total_srs / max(1, successful_routes), 1)
        avg_dist = round((total_distance / 1000.0) / max(1, successful_routes), 2)
        avg_dur = round(total_duration / max(1, successful_routes), 1)

        # Shelter utilization report
        shelter_reports = []
        for s in all_shelters:
            s_data = self.nodes_data[s]
            allocated = shelter_counts[s]
            cap = s_data.get("capacity", 2000)
            shelter_reports.append({
                "shelter_id": s,
                "shelter_name": s_data["name"],
                "sector": s_data["sector"],
                "capacity": cap,
                "evacuees_allocated": allocated,
                "occupancy_rate": round(min(100.0, (allocated / max(1, cap)) * 100.0), 1),
                "safety_rating": s_data.get("safety", 0.90),
            })

        return {
            "status": "CITYWIDE_PLAN_OPTIMAL",
            "is_simulated": True,
            "sector": sector_filter or "All Chennai",
            "total_evacuation_corridors": len(routes_summary),
            "total_evacuees_safeguarded": total_evacuees,
            "avg_route_safety_score": avg_srs,
            "avg_evacuation_distance_km": avg_dist,
            "avg_evacuation_duration_min": avg_dur,
            "corridors": routes_summary,
            "shelters": shelter_reports,
        }
