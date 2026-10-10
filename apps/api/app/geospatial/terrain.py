"""AquaRizz Terrain & Geospatial Feature Extractor (P1-14).

Computes cell-level terrain metrics (Elevation, Slope, HAND, TWI, Imperviousness)
and aggregates ward-level exposure & vulnerability features.
"""
from __future__ import annotations

import math
import numpy as np
from typing import Dict, Any, List


class TerrainFeatureCalculator:
    """Calculates topographic and drainage proxies for 250m analytical cells."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def compute_cell_features(
        self,
        ix: int,
        iy: int,
        center_x_utm: float,
        center_y_utm: float,
        ward_id: str,
    ) -> Dict[str, Any]:
        """Derive physical and urban static features for a 250m grid cell.
        
        Uses Chennai coastal plain priors (elevation 1.5m - 14m, slope 0.2 - 2.5 degrees,
        HAND proxy derived from distance to drainage channels).
        """
        # Chennai coastal gradient: elevation rises gently from east (coast ~80.28) to west (~80.18)
        # In UTM 44N, easting ~ 410,000 to 425,000; northing ~ 1,430,000 to 1,445,000
        norm_easting = (center_x_utm - 410000.0) / 15000.0
        base_elev = 1.5 + 8.0 * max(0.0, min(1.0, 1.0 - norm_easting))
        # Add localized microtopographic noise
        noise = float(self.rng.normal(0.0, 0.4))
        elevation = float(np.clip(base_elev + noise, 0.8, 16.0))

        # Slope in degrees (low in coastal plain)
        slope = float(np.clip(0.3 + float(self.rng.exponential(0.4)), 0.1, 3.5))

        # Height Above Nearest Drainage (HAND) proxy
        dist_drain_m = float(np.clip(100.0 + float(self.rng.exponential(350.0)), 20.0, 1500.0))
        drain_proximity = float(np.clip(1.0 - (dist_drain_m / 1500.0), 0.0, 1.0))
        hand = float(np.clip(elevation * 0.45 + dist_drain_m * 0.002, 0.2, 8.0))

        # Topographic Wetness Index (TWI) = ln(a / tan(beta))
        tan_beta = max(0.001, math.tan(math.radians(slope)))
        flow_acc = max(10.0, 500.0 * (1.0 - drain_proximity) + float(self.rng.exponential(200.0)))
        twi = float(np.clip(math.log(flow_acc / tan_beta), 4.0, 14.0))

        # Built-up imperviousness fraction
        # High in core wards (T. Nagar ~ 0.78), lower in peri-urban
        base_imperv = 0.75 if "112" in ward_id or "113" in ward_id else 0.65
        imperviousness = float(np.clip(base_imperv + float(self.rng.normal(0.0, 0.08)), 0.25, 0.95))

        # Drainage density (km/km2)
        drain_density = float(np.clip(1.8 + float(self.rng.normal(0.0, 0.3)), 0.5, 4.0))

        # Historical flood frequency proxy
        hist_flood_freq = float(np.clip(0.4 + 0.3 * (1.0 - (elevation / 10.0)) + 0.2 * imperviousness, 0.05, 0.95))

        # Composite Static Susceptibility Score (S_cell in [0, 1])
        s_raw = (
            0.25 * (1.0 - np.clip(elevation / 10.0, 0.0, 1.0))
            + 0.20 * (1.0 - np.clip(hand / 5.0, 0.0, 1.0))
            + 0.20 * np.clip(twi / 12.0, 0.0, 1.0)
            + 0.20 * imperviousness
            + 0.15 * drain_proximity
        )
        susceptibility = float(np.clip(s_raw, 0.05, 0.95))

        return {
            "elevation": round(elevation, 2),
            "slope": round(slope, 2),
            "hand": round(hand, 2),
            "twi": round(twi, 2),
            "drain_proximity": round(drain_proximity, 3),
            "drain_density": round(drain_density, 2),
            "imperviousness": round(imperviousness, 2),
            "land_cover": "URBAN_FABRIC" if imperviousness > 0.6 else "OPEN_SPACE",
            "hist_flood_freq": round(hist_flood_freq, 3),
            "susceptibility": round(susceptibility, 3),
        }
