"""AquaRizz Exact Shapley Value Attribution Engine (P2-02).

Computes exact cooperative game theoretic Shapley values for up to 8 feature coalitions
over the deterministic hazard & risk evaluation function.
"""
from __future__ import annotations

import itertools
import math
from typing import Dict, Any, List, Callable, Tuple
import numpy as np


class ExactShapleyExplainer:
    """Computes exact Shapley attribution values over the risk model."""

    def __init__(self, baseline_features: Dict[str, float] | None = None):
        # Canonical baseline: dry catchment conditions
        self.baseline = baseline_features or {
            "rainfall_1h": 0.0,
            "rainfall_3h": 0.0,
            "water_level_m": 0.20,
            "rate_of_rise": 0.0,
            "static_susceptibility": 0.50,
        }

    def explain(
        self,
        target_features: Dict[str, float],
        eval_fn: Callable[[Dict[str, float]], float],
    ) -> List[Dict[str, Any]]:
        """Compute exact Shapley values for each feature in target_features.
        
        Args:
            target_features: Active observed feature vector
            eval_fn: Characteristic function v(S) returning continuous risk in [0, 1]
            
        Returns:
            List of factor attribution dicts containing name, contribution, direction,
            baseline_value, target_value.
        """
        feature_keys = list(target_features.keys())
        n = len(feature_keys)

        # Baseline evaluation
        v_empty = eval_fn(self.baseline)

        shapley_values: Dict[str, float] = {k: 0.0 for k in feature_keys}

        # Iterate over all subset sizes |S| from 0 to n-1
        # Marginal contribution: v(S union {i}) - v(S)
        # Weight = |S|! * (n - |S| - 1)! / n!
        for i, feature_name in enumerate(feature_keys):
            other_features = [k for k in feature_keys if k != feature_name]
            total_marginal = 0.0

            for s_size in range(len(other_features) + 1):
                weight = (
                    math.factorial(s_size)
                    * math.factorial(n - s_size - 1)
                    / math.factorial(n)
                )

                for subset in itertools.combinations(other_features, s_size):
                    # Form coalition S without feature i
                    coalition_without = self.baseline.copy()
                    for f in subset:
                        coalition_without[f] = target_features[f]

                    # Form coalition with feature i
                    coalition_with = coalition_without.copy()
                    coalition_with[feature_name] = target_features[feature_name]

                    v_with = eval_fn(coalition_with)
                    v_without = eval_fn(coalition_without)

                    marginal = v_with - v_without
                    total_marginal += weight * marginal

            shapley_values[feature_name] = total_marginal

        # Format output factors
        results = []
        for k in sorted(shapley_values, key=lambda x: abs(shapley_values[x]), reverse=True):
            val = shapley_values[k]
            results.append({
                "factor_name": k,
                "contribution": round(val, 4),
                "direction": "INCREASES_RISK" if val > 0.001 else ("DECREASES_RISK" if val < -0.001 else "NEUTRAL"),
                "observed_value": target_features[k],
                "baseline_value": self.baseline.get(k, 0.0),
            })

        return results
