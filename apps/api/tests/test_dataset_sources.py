import csv
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

source_validator = importlib.import_module("scripts.validate_chennai_sources")
summarize_kml = source_validator.summarize_kml
summarize_rainfall = source_validator.summarize_rainfall
risk_api = importlib.import_module("app.api.risk")
zones_api = importlib.import_module("app.api.zones")


def test_summarize_rainfall_reports_duplicate_conflicts_and_coverage(tmp_path):
    path = tmp_path / "rainfall.csv"
    rows = [
        {"District": "Chennai", "Station": "Gauge A", "Rainfall": "1.0", "Date": "01-01-2020"},
        {"District": "Chennai", "Station": "Gauge A", "Rainfall": "1.0", "Date": "01-01-2020"},
        {"District": "Chennai", "Station": "Gauge A", "Rainfall": "2.0", "Date": "01-01-2020"},
        {"District": "Chennai", "Station": "Gauge B", "Rainfall": "0", "Date": "02-01-2020"},
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["District", "Station", "Rainfall", "Date"])
        writer.writeheader()
        writer.writerows(rows)

    result = summarize_rainfall(path)

    assert result["rows"] == 4
    assert result["station_name_count"] == 2
    assert result["date_min"] == "2020-01-01"
    assert result["date_max"] == "2020-01-02"
    assert result["duplicate_station_date_keys"] == 1
    assert result["duplicate_extra_rows"] == 2
    assert result["conflicting_duplicate_keys"] == 1
    assert result["units_declared_in_file"] is False
    assert result["station_coordinates_in_file"] is False


def test_summarize_kml_reports_invalid_geometries_without_repair(tmp_path):
    path = tmp_path / "boundaries.kml"
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
          <Placemark><name>valid</name><Polygon><outerBoundaryIs><LinearRing>
            <coordinates>80,13 80.01,13 80.01,13.01 80,13.01 80,13</coordinates>
          </LinearRing></outerBoundaryIs></Polygon></Placemark>
          <Placemark><name>invalid</name><Polygon><outerBoundaryIs><LinearRing>
            <coordinates>80,13 80.01,13.01 80,13.01 80.01,13 80,13</coordinates>
          </LinearRing></outerBoundaryIs></Polygon></Placemark>
        </Document></kml>""",
        encoding="utf-8",
    )

    result = summarize_kml(path)

    assert result["placemarks"] == 2
    assert result["polygon_components"] == 2
    assert result["invalid_polygon_count"] == 1
    assert result["invalid_polygon_examples"][0]["feature"] == "invalid"
    assert result["coordinate_errors"] == []


def test_tnsmart_source_snapshot_has_audited_chennai_points():
    source_path = (
        Path(__file__).resolve().parents[3]
        / "data/raw/chennai/tnsmart-daily-rainfall-page-2026-10-11.html"
    )

    result = source_validator.summarize_tnsmart_daily_page(source_path)

    assert result["embedded_chennai_station_count"] == 63
    assert result["embedded_unique_station_code_count"] == 63
    assert result["embedded_positive_rainfall_count"] == 6
    assert result["embedded_coordinate_error_count"] == 0
    assert result["embedded_numeric_error_count"] == 0
    assert result["embedded_wrong_date_count"] == 0
    assert result["embedded_duplicate_station_codes"] == []
    assert result["source_geojson_point_layer"] is True
    assert result["geodetic_datum_declared"] is False


def test_manifest_validation_supports_checksum_verified_pdf_sources(tmp_path, monkeypatch):
    import hashlib
    import yaml

    source_path = tmp_path / "report.pdf"
    source_bytes = b"%PDF-1.4\nread-only report fixture"
    source_path.write_bytes(source_bytes)
    monkeypatch.setattr(source_validator, "PROJECT_ROOT", tmp_path)
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {
                        "id": "pdf-report",
                        "file": "report.pdf",
                        "size_bytes": len(source_bytes),
                        "sha256": hashlib.sha256(source_bytes).hexdigest(),
                        "format": "PDF",
                        "status": "inspected",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = source_validator.validate_manifest(manifest_path)

    assert result["integrity_ok"] is True
    assert result["sources"][0]["inspection"]["pdf_header_valid"] is True


def test_manifest_validation_rejects_invalid_pdf_header(tmp_path, monkeypatch):
    import hashlib
    import yaml

    source_path = tmp_path / "report.pdf"
    source_bytes = b"not a PDF"
    source_path.write_bytes(source_bytes)
    monkeypatch.setattr(source_validator, "PROJECT_ROOT", tmp_path)
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {
                        "id": "pdf-report",
                        "file": "report.pdf",
                        "size_bytes": len(source_bytes),
                        "sha256": hashlib.sha256(source_bytes).hexdigest(),
                        "format": "PDF",
                        "status": "inspected",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = source_validator.validate_manifest(manifest_path)

    assert result["integrity_ok"] is False
    assert any("PDF header" in message for message in result["errors"])


def test_source_boundaries_are_not_given_invented_risk_scores():
    wards = zones_api.load_ward_collection()
    risks = risk_api.get_all_ward_risks()

    assert len(wards["features"]) == 200
    assert len(risks) == 200
    assert all(risk["risk_level"] == "INSUFFICIENT_EVIDENCE" for risk in risks)
    assert all(risk["risk_score"] is None and risk["confidence"] is None for risk in risks)
    assert any(risk["ward_id"] == "WARD-112" for risk in risks)


def test_risk_lookup_rejects_unknown_ward():
    import fastapi

    try:
        risk_api.get_ward_risk("WARD-NOT-FOUND")
    except fastapi.HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Unknown ward should return 404")
