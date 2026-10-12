"""Cross-check and update Hazard, Exposure, Vulnerability, Impact and Risk Score values.

Runs verification across all 200 GCC divisions and 15 zones.
Updates PostgreSQL and SQLite assessments with mathematically consistent metrics:
  E = e_score (calibrated from population density, imperviousness, road km, critical assets)
  V = v_score (calibrated from low-lying elevation, historical flood frequency, shelter gap)
  I = 0.60 * E + 0.40 * V
  R = H * (0.40 + 0.60 * I)
  Risk Level = Matrix-gated level
"""
import sys
from pathlib import Path

# Add project root and apps/api to path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / "apps" / "api"))

import numpy as np
import psycopg2
import sqlite3
from app.risk.engine import RiskEngine, LEVEL_RANKS, RANK_TO_LEVEL
from app.risk.safety_floors import SafetyFloorEvaluator


def update_postgres():
    print("=" * 60)
    print("Connecting to PostgreSQL database...")
    conn = psycopg2.connect('postgresql://postgres:root@localhost:5432/aquarizz')
    cur = conn.cursor()

    # Fetch all ward features
    cur.execute("""
        SELECT wf.ward_id, wf.e_score, wf.v_score, wf.elevation_mean, wf.susceptibility_mean,
               w.zone, w.name, wf.pop_density
        FROM ward_features wf
        JOIN wards w ON w.id = wf.ward_id
    """)
    ward_feats = {
        row[0]: {
            "e_score": float(row[1]),
            "v_score": float(row[2]),
            "elevation": float(row[3]),
            "susceptibility": float(row[4]),
            "zone": row[5],
            "name": row[6],
            "pop_density": float(row[7]),
        }
        for row in cur.fetchall()
    }
    print(f"Loaded features for {len(ward_feats)} wards.")

    # Fetch all assessments
    cur.execute("""
        SELECT id, ward_id, hazard, hazard_band, water_level_m_val, rainfall_1h_val
        FROM (
            SELECT id, ward_id, hazard, hazard_band,
                   NULL::numeric as water_level_m_val,
                   NULL::numeric as rainfall_1h_val
            FROM assessments
        ) sub
    """)
    # Let's get all assessments
    cur.execute("SELECT id, ward_id, hazard, hazard_band FROM assessments")
    assessments = cur.fetchall()
    print(f"Found {len(assessments)} assessment rows to verify and update.")

    updated_count = 0
    zone_stats = {}

    for aid, wid, hazard, h_band in assessments:
        if wid not in ward_feats:
            continue
        wf = ward_feats[wid]
        e = wf["e_score"]
        v = wf["v_score"]
        impact = round(0.60 * e + 0.40 * v, 4)
        h = float(hazard)
        risk_score = round(float(np.clip(h * (0.40 + 0.60 * impact), 0.001, 0.999)), 4)

        # Matrix gating
        if h_band == "LOW":
            level = "LOW"
        elif h_band == "MEDIUM":
            level = "MEDIUM" if impact < 0.65 else "HIGH"
        elif h_band == "HIGH":
            level = "HIGH" if impact < 0.60 else "VERY_HIGH"
        else:
            level = "VERY_HIGH"

        cur.execute("""
            UPDATE assessments
            SET exposure = %s,
                vulnerability = %s,
                impact = %s,
                risk_score = %s,
                risk_level = %s
            WHERE id = %s
        """, (e, v, impact, risk_score, level, aid))
        updated_count += 1

        z = wf["zone"] or "Unknown"
        if z not in zone_stats:
            zone_stats[z] = {"count": 0, "h": [], "e": [], "v": [], "i": [], "r": []}
        zone_stats[z]["count"] += 1
        zone_stats[z]["h"].append(h)
        zone_stats[z]["e"].append(e)
        zone_stats[z]["v"].append(v)
        zone_stats[z]["i"].append(impact)
        zone_stats[z]["r"].append(risk_score)

    conn.commit()
    conn.close()
    print(f"[OK] Successfully updated {updated_count} assessments in PostgreSQL.")

    print("\n" + "=" * 60)
    print("ZONE-LEVEL CROSS-CHECK & VERIFICATION SUMMARY (PostgreSQL):")
    print(f"{'Zone':<20} | {'Wards':<5} | {'Avg H':<7} | {'Avg E':<7} | {'Avg V':<7} | {'Avg I':<7} | {'Avg Risk':<8}")
    print("-" * 75)
    for z, st in sorted(zone_stats.items()):
        avg_h = sum(st["h"]) / len(st["h"])
        avg_e = sum(st["e"]) / len(st["e"])
        avg_v = sum(st["v"]) / len(st["v"])
        avg_i = sum(st["i"]) / len(st["i"])
        avg_r = sum(st["r"]) / len(st["r"])
        print(f"{z:<20} | {st['count']:<5} | {avg_h:.3f}   | {avg_e:.3f}   | {avg_v:.3f}   | {avg_i:.3f}   | {avg_r*100:.1f}%")
    print("=" * 60)


def update_sqlite():
    db_file = root_dir / "aquarizz.db"
    if not db_file.exists():
        return
    print("\nChecking SQLite database (aquarizz.db)...")
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assessments'")
    if not cur.fetchone():
        conn.close()
        return

    cur.execute("SELECT count(*) FROM assessments")
    cnt = cur.fetchone()[0]
    if cnt == 0:
        conn.close()
        return

    # Fetch ward features if table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ward_features'")
    if not cur.fetchone():
        conn.close()
        return

    cur.execute("SELECT ward_id, e_score, v_score FROM ward_features")
    w_feats = {r[0]: (float(r[1]), float(r[2])) for r in cur.fetchall()}

    cur.execute("SELECT id, ward_id, hazard, hazard_band FROM assessments")
    rows = cur.fetchall()
    upd = 0
    for aid, wid, h, h_band in rows:
        if wid in w_feats:
            e, v = w_feats[wid]
            impact = round(0.60 * e + 0.40 * v, 4)
            h = float(h)
            risk_score = round(float(np.clip(h * (0.40 + 0.60 * impact), 0.001, 0.999)), 4)
            if h_band == "LOW":
                level = "LOW"
            elif h_band == "MEDIUM":
                level = "MEDIUM" if impact < 0.65 else "HIGH"
            elif h_band == "HIGH":
                level = "HIGH" if impact < 0.60 else "VERY_HIGH"
            else:
                level = "VERY_HIGH"

            cur.execute("""
                UPDATE assessments
                SET exposure = ?, vulnerability = ?, impact = ?, risk_score = ?, risk_level = ?
                WHERE id = ?
            """, (e, v, impact, risk_score, level, aid))
            upd += 1

    conn.commit()
    conn.close()
    print(f"[OK] Updated {upd} assessments in SQLite (aquarizz.db).")


if __name__ == "__main__":
    update_postgres()
    update_sqlite()
