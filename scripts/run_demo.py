#!/usr/bin/env python3
"""Verify the local, source-backed AquaRizz prototype and simulated scenario.

Start the API and web app using the commands in README.md, then run this script.
The script reads data and controls only the local demonstration scenario. It
does not create an assessment, approve a review, or dispatch an alert.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx


def request_json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> Any:
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def run_demo(base_url: str) -> None:
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=20.0) as client:
        health = request_json(client, "GET", "/api/v1/health")
        readiness = request_json(client, "GET", "/api/v1/health/ready")
        data_quality = request_json(client, "GET", "/api/v1/data/quality")
        zones = request_json(client, "GET", "/api/v1/zones")
        floods = request_json(client, "GET", "/api/v1/layers/historical-floods/2015")
        rainfall = request_json(client, "GET", "/api/v1/layers/rainfall/tnsmart/2026-10-11")
        current_risk = request_json(client, "GET", "/api/v1/risk")

        if health.get("status") != "ok":
            raise RuntimeError("API health check did not return status=ok")
        if readiness.get("status") != "ready":
            raise RuntimeError("API database readiness check did not return status=ready")
        if data_quality.get("verified_live_source_available") is not False:
            raise RuntimeError("Data quality must not claim that a verified live source is available")
        if len(zones.get("features", [])) != 200 or len(zones.get("zone_features", [])) != 15:
            raise RuntimeError("Processed GCC boundary counts do not match the P0 source audit")
        if len(floods.get("features", [])) != 1212 or len(rainfall.get("features", [])) != 62:
            raise RuntimeError("Processed P0 layer counts do not match the source audit")
        if rainfall.get("dataset_metadata", {}).get("risk_input_eligible") is not False:
            raise RuntimeError("The dated TN-SMART snapshot must remain risk-ineligible")
        if not current_risk or any(
            item.get("risk_level") != "INSUFFICIENT_EVIDENCE"
            or item.get("risk_score") is not None
            for item in current_risk
        ):
            raise RuntimeError("Current risk endpoint must remain fail-closed without verified inputs")

        request_json(client, "POST", "/api/v1/demo/control", json={"action": "reset"})
        peak = request_json(
            client,
            "POST",
            "/api/v1/demo/control",
            json={"action": "advance_to_peak"},
        )
        scenario = peak.get("assessment", {})
        if peak.get("data_classification") != "SIMULATED_SCENARIO":
            raise RuntimeError("Demo scenario is missing its SIMULATED_SCENARIO classification")
        if scenario.get("status") != "SIMULATED_SCENARIO_ONLY" or scenario.get("confidence") is not None:
            raise RuntimeError("Demo scenario status or confidence handling is incorrect")
        if not scenario.get("recommendations") or scenario["recommendations"][0].get("status") != "DRAFT":
            raise RuntimeError("Scenario recommendations must remain drafts")

        request_json(client, "POST", "/api/v1/demo/control", json={"action": "reset"})
        reset_state = request_json(client, "GET", "/api/v1/demo/state")
        if reset_state.get("current_step") != 0:
            raise RuntimeError("Scenario reset did not return to step zero")

    print("AquaRizz local prototype checks passed")
    print(f"  GCC divisions/zones: {len(zones['features'])}/{len(zones['zone_features'])}")
    print(f"  2015 historical inundation polygons: {len(floods['features'])}")
    print(f"  TN-SMART dated station snapshot: {len(rainfall['features'])} points; risk-ineligible")
    print(
        "  Data quality: "
        f"{data_quality['data_status']}; verified live source available="
        f"{data_quality['verified_live_source_available']}"
    )
    print(f"  Current ward risk: {len(current_risk)} wards abstain with no numeric score")
    print(
        "  Simulated exercise peak: "
        f"{scenario['summary']['phase']} / {scenario['risk_level']} / "
        f"index {scenario['risk_score']:.3f} (scenario-only; no confidence or dispatch)"
    )
    print("  Scenario reset: verified")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the locally running AquaRizz API (default: %(default)s)",
    )
    args = parser.parse_args()
    try:
        run_demo(args.base_url)
    except (httpx.HTTPError, RuntimeError, KeyError, TypeError) as exc:
        print(f"Demo verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
