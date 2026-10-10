# ADR-003: Logistic Hazard Function Formulation

## Status
Accepted

## Context
Technical Build Guide 1 proposed a probabilistic-OR formula $H = 1 - (1 - T' \cdot g(S_w))(1 - D_{\text{eff}})$.
Technical Build Guide 2 and Final Technical Guidebook 2 proposed an expert-prior logistic function:
$z = b_0 + \sum w_k f_k$, $H = \sigma((z - b) / T)$ with ramp-normalized features.

## Decision
AquaRizz adopts the calibrated logistic sigmoid hazard function:
$H = \frac{1}{1 + e^{-(z - b) / T}}$
where $z = b_0 + \sum_{k} w_k \cdot \text{ramp}(x_k; \text{lo}_k, \text{hi}_k)$
with cut thresholds:
- LOW: $H < 0.10$
- MEDIUM: $0.10 \le H < 0.40$
- HIGH: $0.40 \le H < 0.70$
- VERY_HIGH: $H \ge 0.70$

## Justification
1. Sigmoidal saturation cleanly handles extreme rainfall spikes without artificial clipping.
2. Directly supports Shapley value factor decomposition via log-odds additivity.
3. Temperature parameter $T$ and bias $b$ allow straightforward Platt scaling / calibration against observed ground truth.
