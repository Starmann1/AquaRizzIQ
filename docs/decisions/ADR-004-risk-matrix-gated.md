# ADR-004: Matrix-Gated Risk Level with Deterministic Safety Floors

## Status
Accepted

## Context
A simple multiplication $R = H \times I$ allows high exposure or vulnerability to produce a false "High Risk" alert even when flood hazard is zero. Conversely, statistical averaging can dilute critical imminent danger.

## Decision
AquaRizz employs a matrix-gated two-step risk assessment:
1. **Hazard Band Gating**: Hazard probability $H$ determines the maximum allowable risk band. If $H$ is in the lowest band, the overall risk cannot exceed LOW regardless of exposure or vulnerability.
2. **Impact Level Selection**: Impact $I = 0.6E + 0.4V$ selects between the base and upper risk category within the gated band.
3. **Safety Floors (F1-F3)**: Deterministic sensor/weather triggers that immediately enforce a floor:
   - **F1**: Sensor capacity fill $\ge 0.85 \implies \text{Floor: HIGH}$
   - **F2**: Sensor fill $\ge 0.60$ and rate of rise $\ge 0.5\text{ cm/min} \implies \text{Floor: MEDIUM}$
   - **F3**: Sustained rainfall intensity $\ge 100\text{ mm/hr} \implies \text{Floor: MEDIUM}$

## Consequences
- Prevents spurious alarms in densely populated wards during clear weather.
- Guarantees immediate alert elevation when physical sensors observe dangerous filling.
