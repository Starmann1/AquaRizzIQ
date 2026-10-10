# ADR-001: Modular Monolith Architecture Pattern

## Status
Accepted

## Context
All four guidebooks evaluate microservices versus modular monolith architectures. For an MVP flood decision support system, microservices introduce inter-service latency, network partitioning risks, distributed transactions, and setup overhead.

## Decision
AquaRizz is built as a single Python FastAPI modular monolith paired with a React TypeScript SPA frontend. All functional domains (geospatial, hydrology, ML forecasting, risk calculation, explainability, agent orchestration, routing) are structured as decoupled Python packages with strictly typed interfaces within the same application process.

## Consequences
- Single development environment and single deployment lifecycle.
- Zero network hop latency between analytical components.
- In-memory data passing via typed Pydantic models.
- Can be modularly extracted into distributed microservices if city-wide enterprise scaling is required in the future.
