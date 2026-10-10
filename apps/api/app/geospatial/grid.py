"""AquaRizz 250m Analytical Grid Generator (P1-14).

Generates regular 250m x 250m grid cells in EPSG:32644 (UTM 44N) and performs spatial joins to GCC wards.
"""
from __future__ import annotations

import math
import uuid
from typing import List, Dict, Any, Tuple
from shapely.geometry import Polygon, MultiPolygon, shape
from app.geospatial.crs import to_utm, to_wgs84

CELL_SIZE_M = 250.0  # Canonical 250m analytical resolution


class GridGenerator:
    """Generates deterministic 250m metric grid cells over ward geometries."""

    def __init__(self, cell_size_m: float = CELL_SIZE_M):
        self.cell_size = cell_size_m

    def generate_cells_for_polygon(
        self, ward_id: str, poly_wgs84: Polygon | MultiPolygon
    ) -> List[Dict[str, Any]]:
        """Generate 250m grid cells covering a given ward polygon.
        
        Args:
            ward_id: Unique ward identifier (e.g., 'WARD-112')
            poly_wgs84: Shapely Polygon in EPSG:4326
            
        Returns:
            List of dicts containing cell metadata and geometries in both UTM and WGS84.
        """
        poly_utm = to_utm(poly_wgs84)
        minx, miny, maxx, maxy = poly_utm.bounds

        # Snap bounding box to 250m grid intervals
        start_ix = math.floor(minx / self.cell_size)
        end_ix = math.ceil(maxx / self.cell_size)
        start_iy = math.floor(miny / self.cell_size)
        end_iy = math.ceil(maxy / self.cell_size)

        cells = []
        for ix in range(start_ix, end_ix):
            for iy in range(end_iy - 1, start_iy - 1, -1):
                cell_minx = ix * self.cell_size
                cell_miny = iy * self.cell_size
                cell_maxx = cell_minx + self.cell_size
                cell_maxy = cell_miny + self.cell_size

                cell_poly_utm = Polygon([
                    (cell_minx, cell_miny),
                    (cell_maxx, cell_miny),
                    (cell_maxx, cell_maxy),
                    (cell_minx, cell_maxy),
                    (cell_minx, cell_miny),
                ])

                # Spatial join: keep cell if it intersects the ward
                if poly_utm.intersects(cell_poly_utm):
                    intersection = poly_utm.intersection(cell_poly_utm)
                    overlap_fraction = intersection.area / (self.cell_size * self.cell_size)
                    
                    cell_poly_wgs84 = to_wgs84(cell_poly_utm)

                    cells.append({
                        "id": str(uuid.uuid4()),
                        "ward_id": ward_id,
                        "ix": ix,
                        "iy": iy,
                        "center_utm": (cell_minx + self.cell_size / 2, cell_miny + self.cell_size / 2),
                        "geom_utm": cell_poly_utm,
                        "geom_wgs84": cell_poly_wgs84,
                        "overlap_fraction": overlap_fraction,
                    })

        return cells
