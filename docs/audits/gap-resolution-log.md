# AquaRizz Collective Gap Resolution Log

This register documents the resolution of every discrepancy identified in `docs/audits/AquaRizz_Collective_Discrepancy_Gap_Register_for_Antigravity.md`.

## P0 — Critical Discrepancies and Gaps

| Gap ID | Topic | Resolution Decision & Enforcement |
|---|---|---|
| **P0-01** | Synthetic vs Real-world Readiness | Added `validation_domain` (`SYNTHETIC`, `OBSERVED`, `MIXED`) and `readiness_status` (`EXPERIMENTAL`, `PROTOTYPE`, `OPERATIONAL`) to `model_versions`. Synthetic models are restricted from operational approval. The UI prominently displays the `SIMULATED` badge. |
| **P0-02** | Prototype Risk Thresholds Separation | Risk policy configuration is stored in immutable, versioned files (`configs/risk.yaml`, `configs/policy.yaml`) and registered in `config_versions` with SHA-256 hashes. Thresholds carry the `PROTOTYPE_ONLY` flag. |
| **P0-03** | Conformal Calibration Specification | Explicitly defined quantile convention (`interpolation='lower'`) and minimum calibration sample size (50) for M2 quantile intervals. Inadequate samples force an explicit fallback to `ABSTAINED`. |
| **P0-04** | Route Validity & Approval Freshness Binding | Human review approvals are cryptographically bound to `assessment_id`, `route_id`, `content_hash`, and alert version. Dispatches fail closed if the hazard assessment exceeds 30 minutes in age. |
| **P0-05** | Real Runtime DB Permissions & Guards | Implemented transactional checks and optimistic concurrency on `decision_cases` and `human_reviews`. Real external emergency dispatch keys are isolated. |

## P1 — Engineering, Model & Governance Gaps

| Gap ID | Topic | Resolution Decision & Enforcement |
|---|---|---|
| **P1-01** | Leakage-Resistant Splits | Enforced 5km Spatial Block Cross-Validation for M1 and storm-event temporal splits for M2. Asserted `no_future` observation timestamps during feature generation. |
| **P1-02** | Quality State Behavioral Matrix | Explicit matrix for `VALID`, `SUSPECT`, `STALE`, `MISSING`, `CONFLICTING`, `OUTLIER`, and `INVALID`. Missing critical gauges triggers `INSUFFICIENT_EVIDENCE`. |
| **P1-03** | Model-API-Frontend Schema Contracts | Unified Pydantic v2 schemas in `apps/api/app/schemas` act as the single source of truth. |
| **P1-04** | Risk Formula Edge Cases | Clamped ramp inputs $\in [0, 1]$, defined explicit tie-breaking, and applied deterministic safety floors (F1-F3). |
| **P1-05** | Spatial & Sensor Coverage Clarity | Ward coverage table documents data sources. Synthetic sensors are prefixed with `SIM-` and flagged `is_simulated=true`. |
| **P1-06** | Evaluation Acceptance Criteria | Specified explicit metrics: M1 PR-AUC, M2 pinball loss & coverage interval, Risk Brier score. |
| **P1-07** | Model/Data/Config Lineage | Every assessment references `assessment_id`, `model_version_id`, `config_version_hash`, and a list of `evidence_ids`. |
| **P1-08** | API Error & Retry Behavior | Standardized on RFC 7807 Problem Details (`{error: {code, message, details, request_id}}`). Supported `Idempotency-Key` headers on mutations. |
| **P1-09** | Cross-Layer Schema Consistency | Database columns, Pydantic fields, and TypeScript interfaces aligned. |
| **P1-10** | Deterministic vs Agent Boundary | Calculations occur in deterministic Python services. Agents communicate via typed `AnalysisState` contracts and cannot execute raw SQL. |
| **P1-11** | LangGraph State Transitions | Defined strictly typed `AnalysisState`. Node retries capped at 1. Transitions logged to `agent_executions`. |
| **P1-12** | Agent Permissions & Abstention Rules | Documented 6-agent permission matrix. Prohibited SQL, unauthorized writes, and alert dispatch from agents. |
| **P1-13** | Human Approval Auditability | Append-only `reviews` table with optimistic concurrency (`content_hash`), checklist requirements, and mandatory operator rationale. |
| **P1-14** | Spatial Reference Discipline | Internal storage and metric computation strictly in EPSG:32644 (UTM 44N). Conversion to EPSG:4326 occurs at API perimeter only. |
| **P1-15** | Hydrological Simulation Honesty | SCS-CN and reservoir models documented as engineering proxies. All outputs marked `SIMULATED`. |
| **P1-16** | Fail-Safe Routing & Semantics | Route cost $c_e = t_e \times (1 + 4 r_e)$. Edges with $r_e \ge 0.9$ dropped. If no path exists, returns explicit `NO_SAFE_ROUTE` with straight-line fallback marked `UNVERIFIED`. |
| **P1-17** | Database Schema Integrity | PostgreSQL foreign keys, check constraints, GIST spatial indices, and UTC timestamptz enforced. |
| **P1-18** | Security Boundaries | RBAC with 6 roles, password hashing with bcrypt/argon2, parameterized queries, and CORS configuration. |
| **P1-19** | Observability for Live Demo | Structured logging with `request_id`, `assessment_id`, and `correlation_id`. Distinct liveness and readiness probes. |
| **P1-20** | Requirement-to-Test Matrix | Traceability matrix published in `docs/requirements/traceability-matrix.md`. |
| **P1-21** | Vertical Slice Testing | 15 integration scenarios mapped to test suite. |
| **P1-22** | Reproducible Native Startup | Dependencies pinned in `requirements.txt` and `package.json`. Makefile targets provided. |
| **P1-23** | Frontend Behavior Verification | Visual indicators for `SIMULATED`, `STALE`, `INSUFFICIENT_EVIDENCE`, and disabled buttons for unauthorized actions. |
