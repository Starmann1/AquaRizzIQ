"""AquaRizz Coordinate Reference System (CRS) Discipline (P1-14).

Storage and metric computations are strictly in EPSG:32644 (UTM Zone 44N).
API boundaries convert to/from EPSG:4326 (WGS 84).
"""
from __future__ import annotations

import pyproj
from shapely.ops import transform
from shapely.geometry.base import BaseGeometry

# Standard SRIDs
INTERNAL_SRID = 32644  # WGS 84 / UTM Zone 44N (metric coordinates)
EXCHANGE_SRID = 4326   # WGS 84 (latitude, longitude in degrees)

# Transformer instances (always_xy=True ensures (lon, lat) order)
_to_utm_transformer = pyproj.Transformer.from_crs(
    f"EPSG:{EXCHANGE_SRID}", f"EPSG:{INTERNAL_SRID}", always_xy=True
)
_to_wgs_transformer = pyproj.Transformer.from_crs(
    f"EPSG:{INTERNAL_SRID}", f"EPSG:{EXCHANGE_SRID}", always_xy=True
)


import shapely

def to_utm(geom: BaseGeometry) -> BaseGeometry:
    """Transform geometry from EPSG:4326 (WGS84 lon,lat) to EPSG:32644 (UTM 44N meters)."""
    return shapely.transform(geom, _to_utm_transformer.transform, interleaved=False)


def to_wgs84(geom: BaseGeometry) -> BaseGeometry:
    """Transform geometry from EPSG:32644 (UTM 44N meters) to EPSG:4326 (WGS84 lon,lat)."""
    return shapely.transform(geom, _to_wgs_transformer.transform, interleaved=False)


def point_to_utm(lon: float, lat: float) -> tuple[float, float]:
    """Transform a single coordinate pair (lon, lat) to UTM (x, y)."""
    x, y = _to_utm_transformer.transform(lon, lat)
    return x, y


def point_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Transform a single UTM coordinate pair (x, y) to WGS84 (lon, lat)."""
    lon, lat = _to_wgs_transformer.transform(x, y)
    return lon, lat
