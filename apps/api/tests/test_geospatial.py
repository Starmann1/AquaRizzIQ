import pytest
from shapely.geometry import Polygon
from app.geospatial.crs import to_utm, to_wgs84, point_to_utm, point_to_wgs84
from app.geospatial.grid import GridGenerator, CELL_SIZE_M
from app.geospatial.terrain import TerrainFeatureCalculator


def test_crs_roundtrip():
    # Chennai coordinates: 80.23, 13.04 (lon, lat)
    lon, lat = 80.23, 13.04
    x, y = point_to_utm(lon, lat)

    # In UTM 44N, x should be ~416,500m, y should be ~1,442,000m
    assert 400000 < x < 450000
    assert 1400000 < y < 1500000

    back_lon, back_lat = point_to_wgs84(x, y)
    assert pytest.approx(back_lon, rel=1e-5) == lon
    assert pytest.approx(back_lat, rel=1e-5) == lat


def test_grid_generation_and_spatial_join():
    generator = GridGenerator(cell_size_m=CELL_SIZE_M)
    # A small polygon around T. Nagar (~1km x 1km)
    poly = Polygon([
        (80.224, 13.035),
        (80.235, 13.035),
        (80.235, 13.045),
        (80.224, 13.045),
        (80.224, 13.035),
    ])

    cells = generator.generate_cells_for_polygon(ward_id="WARD-112", poly_wgs84=poly)
    assert len(cells) > 0

    first_cell = cells[0]
    assert "ix" in first_cell
    assert "iy" in first_cell
    assert "geom_utm" in first_cell
    assert "geom_wgs84" in first_cell
    assert first_cell["overlap_fraction"] > 0.0


def test_terrain_feature_calculator():
    calc = TerrainFeatureCalculator(seed=123)
    feats = calc.compute_cell_features(
        ix=1665,
        iy=5768,
        center_x_utm=416500.0,
        center_y_utm=1442000.0,
        ward_id="WARD-112",
    )

    assert 0.8 <= feats["elevation"] <= 16.0
    assert 0.1 <= feats["slope"] <= 3.5
    assert 0.2 <= feats["hand"] <= 8.0
    assert 4.0 <= feats["twi"] <= 14.0
    assert 0.05 <= feats["susceptibility"] <= 0.95
