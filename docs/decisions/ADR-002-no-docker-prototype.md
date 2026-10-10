# ADR-002: Native Local Execution Without Docker

## Status
Accepted

## Context
Initial specifications considered multi-container Docker Compose. However, containerization creates friction during rapid prototype demonstrations, requires Docker Desktop daemon overhead, and can obscure local networking and process inspection.

## Decision
AquaRizz prototype runs natively on the host workstation. Python virtual environments / native packages run the FastAPI server, and Node.js runs the Vite development server. PostgreSQL and PostGIS run natively on the host. Absolutely no Dockerfiles or Docker Compose configurations are used for the MVP.

## Consequences
- Fast startup, instant rebuilds, zero container virtualization overhead.
- Simple multi-terminal or Makefile startup.
- Full process transparency for live judge demonstrations.
