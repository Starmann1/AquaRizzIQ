# AquaRizz System Architecture Diagram

```mermaid
flowchart TD
    subgraph Data Layer
        SRC[Public & Simulated Data] --> ING[Ingestion & Data Quality Gate]
        ING --> DB[(PostgreSQL + PostGIS\nEPSG:32644)]
    end

    subgraph Analytics & Geospatial
        DB --> GEO[Geospatial Engine\n250m Analytical Grid]
        DB --> HYD[Hydrology Proxy\nSCS-CN + Reservoir]
        GEO --> FEAT[Feature Engineering]
        HYD --> FEAT
        FEAT --> M1[M1: Susceptibility\nLightGBM]
        FEAT --> M2[M2: Water Level Forecast\nLightGBM Quantile]
    end

    subgraph Risk & Explainability
        M1 --> HAZ[Hazard Engine\nH = sigmoid(z-b/T)]
        M2 --> HAZ
        HAZ --> RISK[Matrix-Gated Risk\nH Band x Impact I\nSafety Floors F1-F3]
        RISK --> SHAP[Exact Shapley Attribution\n& Evidence Registry]
    end

    subgraph Agentic Governance
        SHAP --> LG[LangGraph Orchestrator\n6 Typed Agents]
        LG --> POL[Policy Engine]
        POL --> REV{Human Review\nRequired?}
    end

    subgraph Human Oversight & Action
        REV -->|Pending| UI_REV[Human Approval UI\nRole Checklist]
        UI_REV -->|Approved| DISP[Simulated Alert Dispatch]
        UI_REV -->|Approved| ROUTE[Risk-Penalized Routing\nOSMnx + NetworkX]
        DISP --> OUT[Outcome Tracking]
        ROUTE --> OUT
    end
```
