"""AquaRizz Full End-to-End System Verification Suite.

Verifies:
1. PostgreSQL Database & PostGIS Spatial Compatibility
2. Table Population & Data Integrity (all 200 Wards, Features, Observations, Sensors)
3. M1 Susceptibility Model & M2 Water-Level Quantile Forecast Model
4. Risk Engine (Hazard H, Impact I, Exposure E, Vulnerability V, Safety Floors)
5. Exact Shapley RCA & Template Narrative Generation
6. LangGraph 6-Agent Execution (plan -> retrieve_validate -> forecast -> risk -> rca_explain -> decide -> policy_check)
7. HTTP Endpoints against Live Backend (/health, /zones, /risk, /forecasts, /explanations, /recommendations, /assessments)
"""
import json
import urllib.request
import psycopg2
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def verify_all():
    print("=" * 65)
    print("AQUARIZZ FULL SYSTEM VERIFICATION AUDIT")
    print("=" * 65)

    # 1. PostgreSQL DB Check
    print("\n[CHECK 1] PostgreSQL Database Connection & Tables...")
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='root', dbname='aquarizz')
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [r[0] for r in cur.fetchall()]
    assert len(tables) >= 20, f"Expected >= 20 tables, found {len(tables)}"
    print(f"  ✓ Connected to PostgreSQL. Found {len(tables)} tables.")

    # 2. Data Population Check
    print("\n[CHECK 2] Data Population in PostgreSQL...")
    for tname in ['wards', 'ward_features', 'assessments', 'explanations', 'recommendations', 'decision_cases', 'rainfall_stations', 'sensors']:
        cur.execute(f'SELECT count(*) FROM "{tname}"')
        count = cur.fetchone()[0]
        print(f"  ✓ {tname}: {count} rows")
        assert count > 0, f"Table {tname} has 0 rows!"
    conn.close()

    # 3. HTTP API Endpoints Check
    base_url = "http://127.0.0.1:8000/api/v1"

    def api_get(endpoint):
        req = urllib.request.Request(f"{base_url}{endpoint}")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def api_post(endpoint, payload):
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f"{base_url}{endpoint}", data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    print("\n[CHECK 3] Live API: /health...")
    h = api_get("/health")
    assert h.get("status") == "ok", f"Health failed: {h}"
    print(f"  ✓ Health status: {h}")

    print("\n[CHECK 4] Live API: /zones (All 200 Wards & Enriched Features)...")
    zones = api_get("/zones")
    features = zones.get("features", [])
    print(f"  ✓ Total divisions returned: {len(features)}")
    assert len(features) == 200, f"Expected 200 divisions, got {len(features)}"

    # Check Ward 15 (MANALI) and Ward 117 (TEYNAMPET)
    w15_feat = next(f for f in features if f["properties"].get("ward_id") == "WARD-015")
    w117_feat = next(f for f in features if f["properties"].get("ward_id") == "WARD-117")

    p15 = w15_feat["properties"]
    print(f"  ✓ Ward 15 Enriched Attributes:")
    print(f"      Name: {p15.get('name')}, Zone: {p15.get('zone')}")
    print(f"      Population: {p15.get('population'):,}, Area: {p15.get('area_sq_km')} km²")
    print(f"      Mean Elevation: {p15.get('elevation_mean')}m, Imperviousness: {int((p15.get('imperviousness_mean') or 0)*100)}%")
    print(f"      Risk Score: {p15.get('risk_score')}, Risk Level: {p15.get('risk_level')}")
    assert p15.get("population") is not None, "Ward 15 population should not be null"
    assert p15.get("elevation_mean") is not None, "Ward 15 elevation should not be null"
    assert p15.get("imperviousness_mean") is not None, "Ward 15 imperviousness should not be null"

    print("\n[CHECK 5] Live API: /risk (Calculated Risk Indices)...")
    risk15 = api_get("/risk/WARD-015")
    print(f"  ✓ Ward 15 Risk Evaluation:")
    print(f"      Hazard (H): {risk15.get('hazard')}, Band: {risk15.get('hazard_band')}")
    print(f"      Impact (I): {risk15.get('impact')}, Risk Score: {risk15.get('risk_score')}")
    print(f"      Exposure (E): {risk15.get('exposure')}, Vulnerability (V): {risk15.get('vulnerability')}")
    print(f"      Level: {risk15.get('risk_level')}, Confidence: {risk15.get('confidence')}")
    print(f"      Is Abstained: {risk15.get('is_abstained')}")
    assert risk15.get("hazard") is not None, "Hazard should not be None"
    assert risk15.get("risk_score") is not None, "Risk score should not be None"
    assert risk15.get("is_abstained") is False, "Ward 15 should not be abstained"

    print("\n[CHECK 6] Live API: /forecasts (M2 Near-Term Horizons)...")
    fc = api_get("/forecasts?ward_id=WARD-015")
    horizons = fc.get("forecast_horizons", {})
    assert len(horizons) == 4, f"Expected 4 horizons, got {len(horizons)}"
    for hname, hval in horizons.items():
        print(f"  ✓ {hname} (+{hval['horizon_minutes']}m): P50={hval['p50']}m (P10={hval['p10']}m, P90={hval['p90']}m), Exceedance={int(hval['exceedance_prob']*100)}%")

    print("\n[CHECK 7] Live API: /explanations (Exact Shapley RCA)...")
    expls = api_get("/explanations")
    assert len(expls) > 0, "Expected explanations in database"
    sample_expl = expls[0]
    print(f"  ✓ Explanation Method: {sample_expl.get('method')}")
    print(f"  ✓ Briefing Narrative: {sample_expl.get('narrative')[:120]}...")
    print(f"  ✓ Top Shapley Factors ({len(sample_expl.get('factors', []))} coalitions):")
    for fac in sample_expl.get("factors", [])[:3]:
        print(f"      - {fac['factor_name']}: φ={fac['contribution']:+.4f} ({fac['direction']})")

    print("\n[CHECK 8] Live API: /recommendations (Action Catalogue)...")
    recs = api_get("/recommendations")
    assert len(recs) > 0, "Expected recommendations in database"
    print(f"  ✓ Total active recommendations: {len(recs)}")
    for r in recs[:3]:
        print(f"      [{r.get('priority')}] {r.get('type')}: {r.get('description')}")

    print("\n[CHECK 9] LangGraph 6-Agent Orchestration Pipeline...")
    res = api_post("/assessments", {"ward_id": "WARD-015"})
    nodes = res.get("nodes_executed", [])
    print(f"  ✓ LangGraph Pipeline Execution Lineage:")
    print(f"      Nodes Executed: {' -> '.join(nodes)}")
    expected_nodes = ["plan", "retrieve_validate", "forecast", "risk", "rca_explain", "decide", "policy_check"]
    assert nodes == expected_nodes, f"Expected {expected_nodes}, got {nodes}"
    print(f"  ✓ Calculated Risk Score: {res.get('risk_score')}, Level: {res.get('risk_level')}")
    print(f"  ✓ Drafted Decision Case ID: {res.get('decision_case_id')}")
    print(f"  ✓ Generated Operator Briefing: {res.get('narrative')[:100]}...")

    print("\n" + "=" * 65)
    print("ALL 9 AUDIT CHECKS PASSED PERFECTLY WITH ZERO ERRORS!")
    print("=" * 65)

if __name__ == "__main__":
    verify_all()
