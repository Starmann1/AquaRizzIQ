"""AquaRizz M1 Static Susceptibility Model (P0-01, P1-01).

Produces calibrated spatial flood susceptibility rank S in [0, 1] using LightGBM
or deterministic fallback if uncalibrated.
"""
from __future__ import annotations

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List

FEATURE_NAMES = [
    "elevation",
    "slope",
    "hand",
    "twi",
    "drain_proximity",
    "imperviousness",
    "hist_flood_freq",
]


class M1SusceptibilityModel:
    """M1 Spatial flood susceptibility ranking model."""

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path
        self.model = None
        self.validation_domain = "SYNTHETIC"
        self.readiness_status = "PROTOTYPE"
        self.version = "1.0.0"

        if model_path and os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
            except Exception:
                self.model = None

    def predict_susceptibility(self, features: Dict[str, float] | pd.DataFrame) -> float:
        """Compute susceptibility percentile rank S in [0, 1].
        
        Args:
            features: Dictionary or DataFrame row with standard terrain features.
            
        Returns:
            Susceptibility rank in [0.0, 1.0].
        """
        if isinstance(features, dict):
            df = pd.DataFrame([features])
        else:
            df = features

        # Missing features: ensure all required columns exist with safe defaults
        for col in FEATURE_NAMES:
            if col not in df.columns:
                df[col] = 0.5

        X = df[FEATURE_NAMES]

        if self.model is not None:
            try:
                prob = float(self.model.predict_proba(X)[0, 1])
                return float(np.clip(prob, 0.01, 0.99))
            except Exception:
                pass

        # Deterministic Expert-Prior Fallback Formula
        row = X.iloc[0]
        elev_norm = np.clip(1.0 - (row["elevation"] / 10.0), 0.0, 1.0)
        hand_norm = np.clip(1.0 - (row["hand"] / 5.0), 0.0, 1.0)
        twi_norm = np.clip(row["twi"] / 12.0, 0.0, 1.0)
        imperv = np.clip(row["imperviousness"], 0.0, 1.0)
        prox = np.clip(row["drain_proximity"], 0.0, 1.0)

        s_score = (
            0.25 * elev_norm
            + 0.20 * hand_norm
            + 0.20 * twi_norm
            + 0.20 * imperv
            + 0.15 * prox
        )
        return float(np.clip(s_score, 0.05, 0.95))
