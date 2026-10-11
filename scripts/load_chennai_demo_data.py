#!/usr/bin/env python3
"""Initialize the configured database and load bundled Chennai demo layers."""
from __future__ import annotations

import sys
from pathlib import Path

API_PATH = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(API_PATH))

from app.database import SessionLocal, initialize_database_schema  # noqa: E402
from app.services.spatial_datasets import load_bundled_datasets  # noqa: E402


def main() -> int:
    initialize_database_schema()
    with SessionLocal() as session:
        loaded = load_bundled_datasets(session)
    if not loaded:
        print("No processed Chennai datasets were found; the database schema is ready.")
        return 0
    print("Loaded source-backed Chennai datasets into the configured database:")
    for dataset_id, count in loaded.items():
        print(f"  {dataset_id}: {count} features")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
