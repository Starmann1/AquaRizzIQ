# AquaRizz --- Discrepancies, Gaps, and Antigravity Remediation Plan

**Purpose:** Use this document alongside **F2 --- AquaRizz Final
Technical Guidebook 2** as a structured engineering backlog and
implementation audit. It tells Antigravity what to inspect, resolve,
implement, test, and document before AquaRizz can be considered a
well-architected, credible hackathon prototype.

**Important scope and honesty note:** This is a consolidated remediation
specification based on the discrepancies and design concerns identified
in the preceding review. It is **not a claim that every line of all four
guidebooks has been independently re-audited in this document**.
Antigravity must inspect the actual repository and the complete
available guidebooks, identify additional contradictions, and add them
to the same register. Do not silently assume an item is already
implemented merely because a guidebook describes it.

## 0. Instructions to Antigravity

Treat this file as an **engineering audit and remediation contract**,
not as permission to redesign the project from scratch.

1.  Read F2, the current repository, configuration, database migrations,
    API schemas, frontend types, model code, tests, and Docker setup
    before making changes.
2.  Use F2 as the canonical baseline unless a concrete contradiction,
    implementation impossibility, safety defect, or unsupported claim is
    found.
3.  Cross-check G1, G2, and F1 only when necessary to resolve a specific
    discrepancy. Do not merge the guides indiscriminately or reintroduce
    rejected complexity.
4.  Inspect the actual code. For every item, classify it as:
    -   `OPEN` --- not implemented or not specified;
    -   `PARTIAL` --- exists but incomplete or not verified;
    -   `IMPLEMENTED_UNVERIFIED` --- code appears present but
        tests/evidence are missing;
    -   `VERIFIED` --- implementation and relevant tests pass;
    -   `NOT_APPLICABLE` --- with a reason and reviewer confirmation.
5.  Do not mark an item `VERIFIED` from documentation alone. Link each
    verified item to files and tests, and report the actual test command
    and result.
6.  Preserve the prototype deadline. Prioritize a reliable end-to-end
    vertical slice over optional production infrastructure.
7.  Never fabricate datasets, measurements, model metrics, local
    validation, sensor coverage, citations, or successful test results.
8.  Make small, reviewable changes. Avoid broad rewrites, unnecessary
    abstractions, microservices, Kafka, Kubernetes, Redis, vector
    databases, or additional agents unless a concrete requirement
    justifies them.
9.  Keep the prototype honest: synthetic/simulated results must be
    labelled as such, and real-world emergency dispatch must remain
    disabled unless independently authorized and validated.
10. Before coding, return a concise audit report with current status,
    blockers, likely changed files, test plan, and proposed
    implementation order. Then proceed in priority order without asking
    the user to reselect the architecture.


## 0A. Mandatory four-document collective audit (do this before declaring the register complete)

The four source documents in scope are:

- `AquaRizz- Technical buildguide-1.md` (G1)
- `AquaRizz- Technical buildguide-2.md` (G2)
- `AquaRizz — Final Technical Guidebook.md` (F1)
- `AquaRizz — Final Technical Guidebook 2.md` (F2; proposed canonical baseline)

**Do not assume this remediation register already contains every discrepancy.** It captures known issues and required controls from prior reviews. Antigravity must independently inspect all four complete files and extend this register with every additional discrepancy, contradiction, omission, ambiguity, untestable requirement, dependency mismatch, unsupported claim, or implementation blocker found.

### Required audit method

1. Read all four complete documents, not only summaries, headings, tables, or search excerpts.
2. Build a section-level inventory for each document and record its filename, heading, and page/line/section locator where possible.
3. Compare all implementation-critical topics across all four versions:
   - problem-statement alignment, MVP scope, demo-complete definition, geography/AOI, wards/grid, run modes, clocks and time zones;
   - architecture layers, module boundaries, dependency direction, synchronous/asynchronous execution, worker responsibilities, job cadence, idempotency and recovery;
   - stack, package versions, compatibility, dependency pinning, licenses and installability;
   - datasets, availability assumptions, access method, licenses, temporal/spatial resolution, fallbacks, provenance and freshness;
   - raw/processed/training/validation/runtime data separation, labels, synthetic-versus-observed semantics, leakage, snapshots and reproducibility;
   - database tables, columns, types, units, keys, relationships, constraints, triggers, functions, roles, grants, indexes, migrations, retention and immutability;
   - API paths, methods, schemas, units, nullability, status codes, authentication, authorization, pagination, idempotency, errors and frontend consumers;
   - CRS, datum, units, geometry validity, raster alignment, nodata, resampling, spatial joins, grid-to-ward aggregation and spatial indexes;
   - hydrology equations, assumptions, dimensions/units, parameter ranges, numerical stability, simulator interface and anti-circularity;
   - feature definitions, normalization, windows, point-in-time correctness, missingness, imputation, clipping and feature-version compatibility;
   - M1/M2/M3 definitions, training labels, baselines, splits, leakage guards, calibration, uncertainty, metrics, thresholds, model artifacts, runtime fallbacks and promotion;
   - hazard, exposure, vulnerability, impact, confidence, risk aggregation, thresholds, severity floors, boundary conditions and policy versions;
   - explainability method by model type, baseline definition, attribution semantics, additivity/conservation, missing-feature behaviour and evidence links;
   - agents, tool permissions, shared state schemas, retry limits, timeouts, loops, idempotency, abstention, structured outputs and deterministic fallbacks;
   - LangGraph nodes, edges, conditional transitions, checkpointing, resumability, analysis/dispatch separation and persisted state;
   - LLM provider modes, prompt/versioning, grounding, schema validation, prompt injection, timeouts, privacy, cost limits and off-mode behaviour;
   - human review, identity/roles, approval state machine, stale approvals, concurrency, transaction boundaries, dispatch credentials, retries and duplicate prevention;
   - routing graph source/version, edge costs, blocked roads, hazard freshness, route validity, no-safe-route behaviour and route approval binding;
   - frontend page requirements, API types, loading/error/empty/stale states, map layers, accessibility, responsive behaviour and truthful labels;
   - security, secrets, CORS, rate limits, input validation, SQL injection, RBAC, audit tamper resistance and least privilege;
   - observability, logs, correlation IDs, metrics, health/readiness, alerts and incident diagnostics;
   - tests, fixtures, acceptance criteria, test commands, coverage of failure cases and reproducibility;
   - Dockerfiles, Compose dependencies, migrations, seeds, health checks, startup order, clean-machine setup and recovery;
   - implementation phases, prerequisites, file paths, deliverables, ownership, definition of done and deadline-critical sequencing;
   - MVP versus post-MVP/production classifications and any future component accidentally required by the MVP.
4. For each conflict, do not silently choose one. Record what each document says, the chosen resolution, rationale, impact, and test needed to enforce it.
5. For each omission, state why it blocks or weakens implementation, propose the smallest safe default, mark whether it is a decision or an open question, and add an acceptance test.
6. Cross-check every numerical equation for notation, units, input domain, assumptions, clipping, boundary behaviour and implementation-test examples.
7. Cross-check every database entity against API schemas and every API schema against frontend types and test fixtures.
8. Cross-check all state machines against database constraints/functions and adversarial tests.
9. Run a final consistency pass after remediation. A discrepancy is closed only when the specification, implementation and test agree.
10. Preserve a traceability matrix: `requirement/discrepancy ID → source document/section → canonical decision → code/config/migration → test → result`.

### Required output from the audit

Antigravity must update this Markdown file with:

- **Collective discrepancy register:** every finding discovered across G1, G2, F1 and F2, each with a unique ID.
- **Source comparison:** exact conflicting statements or concise paraphrases with document and section references.
- **Severity:** `P0`, `P1`, `P2`, or `P3`, plus the reason.
- **Disposition:** `FIX_NOW`, `SAFE_DEMO_WORKAROUND`, `BACKLOG`, `DECISION_REQUIRED`, or `NOT_APPLICABLE`.
- **Canonical resolution:** one selected implementation, not competing alternatives, unless a genuinely unresolved external decision is unavoidable.
- **Acceptance test:** observable, repeatable pass/fail condition.
- **Repository evidence:** file paths, test names and actual command/result once implemented.
- **Residual risks:** anything that remains open, including the reason it cannot be closed before the demo.

Never claim “all discrepancies have been found” merely because the checklist is complete. State that the audit is exhaustive only relative to the four supplied documents and only after each document has been fully inspected and the cross-reference matrix completed.

### Source-of-truth rule

Use F2 as the proposed canonical baseline for the prototype. G1, G2 and F1 are comparison sources, not parallel implementation authorities. If F2 has a concrete contradiction, unsafe rule, impossible dependency or unsupported claim, document the issue and apply the smallest justified correction to F2. Do not restart architecture selection or perform a wholesale rewrite.

### Deadline rule

Prioritize a demonstrable, reliable vertical slice. Where a production-grade control is not required for a simulated-only demo, use an explicit safe limitation (for example, disable real dispatch) rather than pretending the control is complete. Never weaken or bypass safety controls to make the demo pass.

---

## 1. Priority definitions

-   **P0 --- Safety, integrity, or baseline blocker:** Must be
    explicitly addressed before the affected functionality can be
    trusted. For a demo, some P0 operational capabilities may be
    disabled rather than fully production-hardened.
-   **P1 --- Implementation-contract gap:** Resolve before completing
    the affected module or before freezing the prototype baseline.
-   **P2 --- Quality and hardening:** Implement if time permits or
    record in the backlog with clear acceptance criteria.
-   **P3 --- Post-prototype/production evolution:** Not a hidden MVP
    dependency.

A "winning prototype" means a clear, credible, reproducible
demonstration of the core problem-to-decision flow. It does **not** mean
a production-certified flood warning service.

------------------------------------------------------------------------

# 2. P0 --- Critical discrepancies and gaps

## P0-01. Synthetic validation must not be confused with real-world readiness

**Risk:** A model that performs on simulated data could be presented as
validated for Chennai, even though synthetic data does not establish
real-world predictive performance.

**Required work** - Add explicit metadata to each model version: -
`validation_domain` (for example, `SYNTHETIC`, `REAL`, or `MIXED`); -
`readiness_status` (for example, `DEVELOPMENT`, `SYNTHETIC_VALIDATED`,
`REAL_DATA_EVALUATED`, `OPERATIONALLY_APPROVED`); - training/evaluation
dataset identifiers and versions; - geographic and temporal coverage; -
evaluation date and metrics; - approver and approval timestamp where
applicable. - Define allowed transitions between readiness states. -
Make the model domain and readiness status available in API responses
and visible in the UI. - Prevent synthetic-only models from being
described as operationally validated or used to authorize operational
warning claims. - Ensure synthetic data, observed data, derived
features, assumptions, and model outputs are distinguishable in storage
and UI.

**Acceptance tests** - A synthetic-only model is clearly labelled in the
dashboard and API. - Attempting to mark a synthetic-only model
operationally approved is rejected unless the required real-data
validation and approval conditions are met. - A model with missing
readiness metadata cannot silently enter a real-world warning path.

## P0-02. Prototype risk thresholds must be separated from approved warning thresholds

**Risk:** Deterministic code and configured thresholds may look
authoritative even when they are only engineering priors.

**Required work** - Version the risk policy and record its status, such
as `DRAFT`, `PROTOTYPE_ONLY`, `LOCALLY_VALIDATED`, and
`OPERATIONALLY_APPROVED`. - Record policy parameters, geographic scope,
supporting evidence, validation period, approver, effective date, and
change history. - Define which policy states can be used for
demonstration, internal review, or operational warnings. - Display the
policy status and the fact that prototype thresholds are not locally
validated where appropriate. - Do not imply that prototype weights are
scientifically validated Chennai coefficients. - Ensure configuration
changes create a new version or auditable change record; do not mutate
the meaning of past assessments.

**Acceptance tests** - A prototype-only policy can produce a demo
classification but cannot authorize an operational warning. - Each
assessment identifies the exact policy version used. - A changed policy
does not silently rewrite previous assessment results.

## P0-03. Conformal calibration and prediction intervals must be fully specified

**Risk:** Engineers could implement different statistical conventions
and obtain different interval endpoints or make unsupported coverage
claims.

**Required work** - Inspect the actual M2 quantile and calibration
formulation in F2 and code. Do not substitute a different method without
recording an architecture decision. - State the exact calibration score,
quantile/order-statistic convention, finite-sample index rule, tie
handling, missing-observation handling, and minimum calibration sample
size. - Explicitly decide whether negative interval adjustments are
permitted. Document the selected method and its consequences; do not
leave this as an implementation guess. - Define behaviour when the
required order statistic cannot be obtained or the calibration set is
too small: mark calibration unavailable or abstain rather than inventing
a valid interval. - Evaluate each forecast horizon independently where
the method requires it. - Document assumptions and limitations,
including the fact that distribution shift can undermine empirical
coverage. - Keep synthetic calibration distinct from real-data
calibration. - Provide fixed test fixtures with known calibration scores
and expected adjustment/interval endpoints.

**Acceptance tests** - The same versioned calibration dataset and
configuration produce identical results on repeated runs. - Boundary
cases (empty set, insufficient set, ties, missing labels, extreme
scores) follow documented behaviour. - UI/API never imply validated
real-world coverage from synthetic-only calibration.

## P0-04. Route validity, hazard freshness, and approval must be bound together

**Risk:** A route approved against an earlier hazard assessment or road
graph may be stale at dispatch time.

**Required work** - Attach to every route result: - route ID and/or
deterministic route hash; - graph/version identifier; - hazard
assessment ID and version; - relevant data/as-of timestamp; - creation
timestamp and validity/expiry time; - routing policy/configuration
version. - Bind the human approval to the exact route and the versions
it reviewed. - At dispatch time, re-check that the route remains within
its validity window and that the referenced hazard and graph versions
are still valid. - Invalidate or require renewed review when the route,
graph, hazard assessment, or relevant policy changes. - Fail closed on
missing metadata, stale routes, expired approvals, or version
mismatch. - If the prototype cannot implement a complete freshness
protocol in time, disable dispatch for stale routes and demonstrate only
simulated, reviewable dispatch.

**Acceptance tests** - A route cannot be dispatched after expiry. -
Changing the hazard or graph version after approval blocks dispatch
until revalidation and required approval. - Missing route version
metadata never defaults to "safe."

## P0-05. Verify approval and dispatch enforcement against real runtime database permissions

**Risk:** A documented database trigger or function does not prove that
actual runtime roles and transactions prevent bypasses.

**Required work** - Identify every code path that can approve, reject,
expire, publish, or dispatch an alert. - Ensure application/agent roles
do not have arbitrary privileges to bypass controlled state
transitions. - Use transactions and appropriate concurrency control for
approval and dispatch state transitions. - Define and enforce the
canonical state machine, including permitted transitions and terminal
states. - Add idempotency handling for duplicate requests and dispatch
attempts. - Test concurrent approvals, concurrent dispatch attempts,
stale approvals, expired approvals, rejection, and failed downstream
dispatch. - Ensure failed operations do not leave partially updated
state or falsely claim dispatch succeeded. - Keep real emergency
dispatch credentials out of agent processes; use a simulated dispatch
adapter for the prototype. - Record reviewer identity, decision,
timestamp, rationale where applicable, assessment/policy/model versions,
and dispatch result.

**Acceptance tests** - Unauthorized roles cannot invoke privileged
operations. - Duplicate requests do not cause duplicate dispatch. -
Rejected, expired, stale, or mismatched approvals are refused. -
Failure/rollback leaves consistent state and an auditable outcome. - The
application reports dispatch success only after the dispatch adapter
confirms success.

------------------------------------------------------------------------

# 3. P1 --- Model, data, and contract gaps

## P1-01. Specify leakage-resistant training and evaluation splits

**Required work** - Specify exact spatial and temporal split rules
appropriate to each model and dataset. - Prevent preprocessing,
normalization, imputation, feature selection, calibration, or threshold
tuning from using held-out data. - Fix random seeds where applicable and
record them. - Define baselines and model-selection criteria before
evaluation. - Record split IDs and dataset versions so results are
reproducible. - Document how repeated observations from the same
sensor/location and correlated time periods are handled. - Do not claim
model performance if there is no appropriate held-out evaluation
dataset.

**Acceptance tests** - A reproducible split can be regenerated from
recorded metadata. - Tests or validation scripts verify that held-out
data is not used during fitting/calibration. - Metrics include the
evaluation dataset and split identifiers.

## P1-02. Define deterministic missing/stale/conflicting-input behaviour

The quality states include `VALID`, `SUSPECT`, `STALE`, `MISSING`,
`CONFLICTING`, `OUTLIER`, and `INVALID`. Define how each state affects
every relevant input path.

**Required work** - Set configurable freshness limits per source and
input type. - Specify whether each state is accepted, down-weighted,
excluded, causes degradation, triggers abstention, or causes request
rejection. - Do not treat stale values as current. - Define conflict
detection, tolerances, source precedence (if any), and how unresolved
conflicts are exposed. - Track which required inputs were
missing/stale/conflicting for every assessment. - Ensure confidence is
not a vague score that silently conceals data problems.

**Acceptance tests** - Each quality state has deterministic expected
behaviour. - Stale and conflicting values are visible in API/UI and in
the audit record. - Insufficient required evidence produces an explicit
state and reason rather than a fabricated prediction.

## P1-03. Establish contracts between M1, M2, M3, risk, API, and frontend

**Required work** For every model/service contract, define: - input and
output schema; - units and valid ranges; - timestamps and timezone
convention; - spatial identifier/CRS where applicable; - nullability and
missing-value behaviour; - confidence/uncertainty meaning; - model and
configuration version; - expected errors and abstention states; - schema
version and compatibility expectations.

Ensure the same definitions are used in Pydantic schemas, persistence
models, API responses, frontend TypeScript types, and LangGraph state.

**Acceptance tests** - Contract tests verify the API schema and frontend
types agree. - Invalid units, missing identifiers, invalid timestamps,
and unsupported schema versions are rejected clearly. - Model outputs
cannot be confused with hazard scores, risk scores, or calibrated
probabilities.

## P1-04. Make risk formula and classification edge cases exact

**Required work** - Define normalization bounds, clipping behaviour,
missing-feature handling, weights, thresholds, and units. - State
inclusive/exclusive threshold boundaries and precedence when rules
conflict. - Define the exact interaction between hazard ceilings, impact
selection, safety floors, and confidence gates. - Ensure exposure cannot
silently dominate hazard. - Define whether an output is a susceptibility
score, hazard score, engineered risk score, probability, or categorical
class. Never use these labels interchangeably. - Version all weights and
thresholds. - Include example calculations with clearly labelled
illustrative inputs.

**Acceptance tests** - Boundary tests cover values immediately below,
at, and above each threshold. - Property tests verify required
invariants, including that confidence cannot silently lower a required
safety severity. - Example calculations match implementation output
exactly.

## P1-05. Clarify spatial and sensor coverage in the prototype

The reviewed design describes simulated sensors in an area of interest
and a rainfall-plus-static-feature variant for other wards. Verify the
exact counts and coverage against F2 and implementation rather than
assuming they are correct.

**Required work** - Document which wards have simulated sensors, which
have real/public data, and which use only static or fallback features. -
Record source and quality state at ward/grid level. - Make coverage gaps
visible on the map and ward detail view. - Simulate normal, rising,
threshold-crossing, rapid-rise, dropout, stale, noisy, contradictory,
and extreme-event conditions. - Keep simulator output behind the same
validated ingestion interface used for sensor data. - Avoid presenting
simulated sensor locations or readings as real installations.

**Acceptance tests** - The UI visibly distinguishes observed/public,
simulated, derived, and missing data. - Each scenario is reproducible
using a fixed seed or recorded scenario configuration. - Coverage gaps
lower confidence or trigger abstention according to explicit rules.

## P1-06. Define evaluation acceptance criteria before interpreting metrics

**Required work** - M1: define ROC-AUC, PR-AUC, precision, recall, F1,
calibration, class imbalance handling, and the baseline comparison. -
M2: define MAE/RMSE, whether MAPE is valid for the target,
horizon-specific performance, interval coverage/width, and lead-time
evaluation. - M3: define ROC-AUC/PR-AUC, Brier score, calibration, and
confusion-matrix reporting where labels support them. - Risk policy:
measure high-severity precision, false-alert rate, missed-event rate,
lead time, and calibration where ground truth exists. - Routing: test
route validity, blocked-edge avoidance, risk exposure, and no-route
behaviour. - Agents: measure evidence grounding, policy compliance,
abstention correctness, tool failures, and human overrides. - Define
sample-size requirements and how to report "not evaluated" when evidence
is insufficient. - Do not invent target metrics or claim performance
based solely on synthetic scenarios.

**Acceptance tests** - Evaluation reports include dataset/version,
split, sample count, metric definition, and uncertainty/limitations. -
Missing real ground truth is reported as a limitation rather than
replaced by unsupported accuracy claims.

## P1-07. Make model/data/configuration lineage complete

**Required work** Each assessment/forecast should reference: -
assessment ID and creation time; - input/data snapshot ID or immutable
references to all input records; - source timestamps and quality
states; - feature-generation version; - model version; -
risk-policy/configuration version; - spatial unit and CRS where
relevant; - evidence IDs; - agent execution/correlation IDs where
applicable; - output status, abstention reason, and explanation version.

**Acceptance tests** - An assessment can be reconstructed or its exact
input snapshot retrieved. - New model/configuration versions do not
rewrite the provenance of old assessments. - Audit views show the
versions used for a given result.

## P1-08. Standardize API error and retry behaviour

**Required work** - Define consistent error envelopes and stable error
codes. - Distinguish validation errors, unavailable dependencies, stale
inputs, insufficient evidence, model errors, authorization failures,
conflicts, and internal errors. - Define timeout and retry policy by
operation. Do not retry non-idempotent dispatch blindly. - Use
idempotency keys where repeated requests could create duplicate
assessments, reviews, or dispatch attempts. - Define
pagination/filtering and sensible response-size limits for list/map
endpoints. - Ensure health and readiness endpoints distinguish process
health from dependency readiness. - Never expose secrets or sensitive
internals in errors.

**Acceptance tests** - Frontend handles all documented error
categories. - Retried idempotent requests do not duplicate side
effects. - The API communicates abstention as a valid domain result, not
a generic server error.

## P1-09. Ensure API, database, and frontend schema consistency

**Required work** - Cross-check every endpoint against actual
request/response models and database entities. - Verify spatial fields,
identifiers, enums, timestamps, and units. - Generate or validate
frontend types from the API schema where practical. - Ensure review and
dispatch APIs cannot accept client-supplied fields that should be
server-controlled (for example, reviewer identity, approval state,
dispatch success, or model status). - Verify access control on every
sensitive endpoint.

**Acceptance tests** - Contract tests cover success and failure
responses. - Client input cannot forge trusted server-side state. -
Schema changes are accompanied by migrations and compatibility tests.

------------------------------------------------------------------------

# 4. P1 --- Agentic AI, LLM, and human-governance gaps

## P1-10. Enforce the boundary between deterministic computation and agent narration

**Required work** - Keep numeric forecast, hazard, risk, confidence,
policy, and route-cost calculations in deterministic, tested services. -
Agents call typed service/repository interfaces; they do not execute
arbitrary SQL or bypass business logic. - LLM output may summarize
validated evidence and recommend from approved action catalogs, but may
not invent observations, change numeric outputs, set thresholds, approve
alerts, or dispatch. - Provide `LLM_MODE=off`, `template`, and optional
`llm` modes if supported by the canonical design. - Validate structured
LLM output against a schema and verify every factual claim is linked to
available evidence. - If LLM generation fails, use deterministic
templates or return a clear unavailable state. - Treat retrieved text
and external content as untrusted input, not instructions.

**Acceptance tests** - The system produces core risk results with the
LLM disabled. - Invalid or unsupported LLM claims are rejected or
replaced with a safe fallback. - LLM failure does not alter numerical
outputs or approval state.

## P1-11. Verify LangGraph state transitions and failure handling

**Required work** - Define typed shared-state fields and ownership of
each field. - Specify stage inputs, outputs, retries, timeouts,
idempotency, and failure/abstention transitions. - Separate analysis
from dispatch; dispatch must read the current persisted approval state
and revalidate relevant versions. - Prevent retries from duplicating
side effects. - Log node execution, tool results, errors, model/policy
versions, and correlation IDs. - Define whether interrupted runs resume,
restart, or require review.

**Acceptance tests** - Graph tests cover success, tool failure, retry,
missing evidence, model unavailable, LLM unavailable, and interrupted
execution. - Dispatch nodes cannot run from an in-memory "approved" flag
alone. - A failed node does not silently create a complete-looking
assessment.

## P1-12. Specify each agent's permissions and abstention rules

For every canonical agent, verify that the guide and implementation
state: - purpose and allowed tools; - typed inputs and outputs; -
prohibited actions; - evidence requirements; - insufficient-data
behaviour; - retries and idempotency; - logging; - human escalation; -
failure output.

The six-agent design should not be expanded just to make the system look
more agentic. If a deterministic function is sufficient, prefer the
function.

**Acceptance tests** - Agent tests assert permitted and prohibited tool
use. - Agents cannot directly dispatch, alter thresholds, change model
versions, or write arbitrary SQL. - Evidence-deficient tasks result in
explicit abstention/escalation.

## P1-13. Make human approval unambiguous and auditable

**Required work** - Define legal state transitions and terminal
states. - Bind approval to assessment, policy/model versions, route (if
applicable), and relevant expiry. - Enforce reviewer authorization on
the server. - Record reviewer identity, timestamp, decision, rationale,
and version/hash of the content reviewed. - Revalidate at dispatch
time. - Make rejection, expiry, stale approval, and failed dispatch
visible to the reviewer. - Use simulated dispatch for the hackathon
unless real integration is explicitly authorized and independently
validated.

**Acceptance tests** - No dispatch is possible without a valid persisted
approval. - Changed content or relevant versions invalidate the
approval. - Every decision and dispatch attempt appears in audit
history.

------------------------------------------------------------------------

# 5. P1 --- Geospatial, hydrology, and routing gaps

## P1-14. Make spatial reference systems and spatial joins explicit

**Required work** - Declare the source CRS and chosen projected CRS for
distance/area analysis in Chennai; verify the selection rather than
assuming a CRS. - Transform coordinates explicitly and validate geometry
SRIDs. - Define geometry validity handling, invalid polygon repair
policy, coordinate-order conventions, and units. - Keep spatial joins
reproducible and avoid mixing degrees with metre-based calculations. -
Define grid-to-ward assignment rules for boundary cells and partial
intersections. - Document raster resampling, nodata handling,
resolution, alignment, and aggregation rules. - Validate ward boundaries
and ensure the UI does not imply false precision from 250 m grid cells.

**Acceptance tests** - Known control locations map to expected areas
within documented tolerance. - Geometry and CRS tests detect invalid or
mismatched spatial inputs. - Raster nodata and boundary cases have
deterministic outcomes.

## P1-15. Keep the hydrological simulator scientifically honest

**Required work** - Label the simplified SCS Curve Number runoff
approximation, linear reservoir, Manning-based capacity proxy, and
simulated water levels as prototype approximations. - Document units,
assumptions, valid input ranges, parameter provenance, and limitations
for every equation. - Do not present the simulator as a validated
Chennai hydraulic model or replacement for SWMM/HEC-RAS/MIKE. - Ensure
simulator data enters through the same schema/validation boundary as
real sensor data. - Define stable, reproducible scenarios and fault
injection. - Keep simulated values and real observations distinguishable
in persistence, APIs, charts, and map layers.

**Acceptance tests** - Unit tests verify dimensions/ranges and expected
qualitative behaviour. - Invalid inputs fail explicitly. - Simulator
outputs are always labelled `SIMULATED` and cannot be mistaken for
observed telemetry.

## P1-16. Make routing fail safe and explain its result

**Required work** - Define units and interpretation for base travel cost
and each flood-risk, road-susceptibility, and critical-hazard penalty. -
Define which edge attributes are required and how missing/stale
edge-risk data is handled. - Define blocked-edge semantics and what
happens if all routes are blocked. - Include route version, hazard
timestamp, graph version, cost configuration, and validity window. -
Explain why a route was selected and which risk penalties affected it. -
Do not claim a route is safe in an absolute sense; describe it as the
lowest-cost route under the current graph and risk assumptions. - Keep
routing unavailable/abstention distinct from `NO_SAFE_ROUTE`.

**Acceptance tests** - Blocked edges are never used. - No valid route
produces `NO_SAFE_ROUTE`. - Missing graph or stale hazard data does not
produce a falsely reassuring route. - Route results are reproducible for
the same graph, inputs, and configuration.

------------------------------------------------------------------------

# 6. P1 --- Database, security, and operational integrity

## P1-17. Verify database schema and constraints against application behaviour

**Required work** - Cross-check entities and relationships against API
models, service methods, and UI needs. - Verify primary/foreign keys,
uniqueness, check constraints, spatial indexes, time indexes, and query
indexes. - Define deletion/retention behaviour for audit, evidence,
model versions, and outcomes. - Store timestamps consistently and define
UTC/local display conventions. - Ensure historical assessments retain
their model/configuration/provenance references. - Use migrations; do
not depend on ad hoc manual schema changes. - Verify transaction
boundaries for assessment creation, review, and dispatch.

**Acceptance tests** - Fresh database creation and migrations succeed. -
Invalid state combinations are rejected. - Referential integrity is
preserved when operations fail or are retried.

## P1-18. Verify security boundaries in the actual prototype

**Required work** - Define authentication and role-based authorization
appropriate to the demo. - Protect review/approval endpoints from
unauthorized use. - Validate all external/API input with schemas and
sensible limits. - Use parameterized queries/ORM patterns; prohibit
arbitrary SQL generated by agents. - Keep secrets in environment/secret
configuration, never source control. - Configure CORS, secure headers,
and rate limiting where appropriate to the exposed environment. - Avoid
logging secrets or sensitive personal information. - Isolate dispatch
credentials from agents; use a mock adapter for demo dispatch. - Check
that debug mode and permissive development settings are not accidentally
exposed.

**Acceptance tests** - Unauthorized and malformed requests are
rejected. - Secrets are absent from repository and logs. - Agent tools
cannot escalate privileges or invoke restricted actions.

## P1-19. Make observability sufficient to debug a live demo

**Required work** - Use structured logs and stable request, assessment,
correlation, and agent execution IDs. - Record model version,
policy/configuration version, data snapshot, latency, failures,
abstentions, and review/dispatch status. - Provide health/readiness
checks and actionable errors. - Ensure a demo operator can diagnose an
ingestion, model, database, or frontend failure without guessing. -
Optional Prometheus/Grafana must not be required for the MVP unless
explicitly selected.

**Acceptance tests** - A single assessment can be traced from input
through output, review, and simulated dispatch. - Logs identify the
failed stage and error category without leaking secrets. - Health checks
accurately distinguish service liveness from dependency readiness.

------------------------------------------------------------------------

# 7. P1 --- Testing and reproducible build gaps

## P1-20. Create a requirement-to-test traceability matrix

For every requirement, record: - requirement ID; - component/file; -
test file and test name; - command to run; - expected result; - current
status; - evidence from the run.

At minimum, cover data ingestion, data quality, spatial processing,
M1/M2/M3, risk policy, attribution/explanation, abstention, agents,
approval, dispatch simulation, routing, provenance, and frontend flows.

## P1-21. Test the whole vertical slice

Required scenarios: 1. Normal conditions. 2. Heavy rainfall and rising
simulated water levels. 3. Threshold crossing and risk escalation. 4.
Missing rainfall. 5. Stale sensor readings. 6. Contradictory sensor
readings. 7. Forecast/model unavailable. 8. LLM unavailable with
fallback. 9. Insufficient historical data. 10. Missing or incompatible
model version. 11. No route available. 12. Route expires after approval.
13. Approval rejected or expired. 14. Duplicate approval/dispatch
request. 15. Database/worker restart or temporary dependency failure.

**Acceptance tests** - The core demo succeeds from a clean start. -
Every failure scenario yields an explicit, safe state and a visible
explanation. - No scenario invents evidence or claims a side effect
succeeded when it did not.

## P1-22. Verify reproducible installation and startup

**Required work** - Pin compatible dependency versions. - Provide
`.env.example` without secrets. - Verify Dockerfiles and Docker Compose
service dependencies, health checks, migrations, and seed-data
loading. - Provide one documented command sequence for clean setup,
start, tests, and demo reset. - Ensure a clean checkout can start
without undocumented manual steps. - Record external data dependencies
and provide deterministic fixtures/fallbacks for an offline demo. -
Ensure startup errors identify missing configuration instead of silently
continuing in a broken state.

**Acceptance tests** - A clean environment can install/build and start
the MVP using documented steps. - Database migrations and seed scripts
are repeatable. - Demo reset restores a known baseline state.

## P1-23. Verify frontend behaviour, not just visual appearance

**Required work** - Clearly label synthetic/simulated data and
prototype-only policy/model states. - Display timestamps, freshness,
coverage, confidence/uncertainty, and abstention reasons. - Handle
loading, empty, stale, error, and unavailable states. - Ensure the map
legend and risk colours have consistent meanings. - Make ward details,
evidence, explanation, review, route, and audit history traceable to the
same assessment ID. - Prevent double-clicking or retries from creating
duplicate review/dispatch actions. - Ensure the interface remains usable
at the intended demo resolution.

**Acceptance tests** - Browser tests cover normal, high-risk,
insufficient-evidence, rejected-review, and no-route flows. - The UI
does not display missing values as zero or stale values as live. -
Review and dispatch status shown in the UI matches persisted backend
state.

------------------------------------------------------------------------

# 8. P2 --- Prototype quality and competitive differentiation

These improve clarity and judging quality but must not displace core
correctness.

## P2-01. Make the end-to-end story immediately understandable

-   Show the chain: **SENSE → PREDICT → ASSESS → EXPLAIN → DECIDE →
    HUMAN REVIEW → SIMULATED ALERT/ROUTE → OUTCOME**.
-   Provide a small set of reproducible scenario controls.
-   Show before/after changes in rainfall, water level, hazard, and
    risk.
-   Explain why a ward changed classification using actual calculated
    outputs and evidence IDs.
-   Clearly distinguish observed, public, simulated, derived, modelled,
    assumed, prototype, and validated information.

## P2-02. Demonstrate explainability honestly

-   Use model-appropriate attribution or deterministic rule traces.
-   Do not hard-code example percentages.
-   Record the baseline, feature values, contribution method, and
    version.
-   Distinguish feature attribution from causal proof. A contribution
    score does not automatically establish physical causation.
-   Include missing-feature and unavailable-attribution behaviour.

## P2-03. Make recommendations actionable but bounded

-   Use a controlled catalog of recommendation types and required
    evidence.
-   Include reason, affected ward/location, urgency, assumptions,
    confidence, and human-review requirement.
-   Do not make unsupported evacuation or emergency instructions.
-   Keep recommendations as drafts until approved under the prototype
    policy.

## P2-04. Improve demo reliability

-   Add a deterministic scenario reset.
-   Keep a fallback dataset and mock dispatch adapter.
-   Prepare a known-good walkthrough and one failure demonstration.
-   Ensure no network access is required for the core demo unless
    explicitly stated.
-   Avoid adding services that make startup fragile.

## P2-05. Document limitations prominently

-   No claim of validated Chennai flood forecasting from synthetic data.
-   No claim of real dense sensor coverage unless verified.
-   No claim of a validated city-scale hydraulic model.
-   No claim of real emergency integration if only simulated.
-   No performance/accuracy claim without a defined, suitable evaluation
    dataset.

------------------------------------------------------------------------

# 9. P3 --- Post-prototype/production evolution; not MVP dependencies

Do not implement these merely to make the architecture look advanced: -
Kafka or other event-streaming infrastructure; - MQTT broker and real
sensor hardware; - Kubernetes; - Redis; - vector database; -
production-scale object storage; - OSRM/GraphHopper unless MVP routing
demonstrably needs them; - real emergency alert integrations; - advanced
deep learning replacing LightGBM without genuine held-out evidence; -
full hydraulic modelling with SWMM/HEC-RAS/MIKE without data, expertise,
and validation; - production OIDC/enterprise identity unless required by
the actual deployment; - full Prometheus/Grafana stack if structured
logs and simple health metrics suffice for the demo.

For each future component, record the concrete requirement that would
justify introducing it.

------------------------------------------------------------------------

# 10. Cross-document and repository consistency audit

Antigravity must perform this audit against the **actual contents** of
F1, F2, G1, and G2, plus the current code. Add any newly discovered
discrepancy to this file.

## Architecture and scope

-   [ ] One canonical architecture is stated and implemented.
-   [ ] Modular monolith remains the MVP default unless a documented
    blocker justifies otherwise.
-   [ ] MVP versus future/production components are unambiguous.
-   [ ] Demo mode and operational mode are clearly separated.
-   [ ] Every required component has a purpose and a defined interface.

## Data and geospatial

-   [ ] Data source access, licence, resolution, temporal cadence,
    preprocessing, fallback, and limitations are documented where known.
-   [ ] Real/public, simulated, derived, and missing data are
    distinguishable.
-   [ ] Ward/grid relationships and boundary rules are explicit.
-   [ ] CRS, geometry validity, raster nodata, units, and spatial joins
    are tested.
-   [ ] Sensor simulator schema matches ingestion schema.

## Numerical and ML

-   [ ] Every equation has defined notation, units, assumptions, valid
    ranges, and limitations.
-   [ ] Prototype parameters are labelled as assumptions/engineering
    priors.
-   [ ] M1, M2, and M3 roles are distinct.
-   [ ] Model input/output contracts match persisted data and APIs.
-   [ ] Training/evaluation split and leakage controls are reproducible.
-   [ ] Metrics are tied to dataset versions and appropriate ground
    truth.
-   [ ] Synthetic validation is not presented as real-world validation.
-   [ ] Confidence, uncertainty, hazard, risk, and probability are not
    conflated.
-   [ ] Calibration algorithm and edge cases are precisely specified.

## Risk, explainability, and evidence

-   [ ] Risk formula, thresholds, and precedence rules are
    deterministic.
-   [ ] Exposure does not silently dominate hazard.
-   [ ] Safety floors and confidence gates are covered by tests.
-   [ ] Attribution method matches each model type.
-   [ ] Attribution is calculated, not hard-coded.
-   [ ] Evidence references trace to input data and versions.
-   [ ] Explanations do not imply causal proof without evidence.

## Agents, LLM, and governance

-   [ ] Agents use typed tools/services, not arbitrary SQL.
-   [ ] Agent permissions and prohibited actions are explicit.
-   [ ] LLM cannot alter numerical results or approve/dispatch.
-   [ ] LLM-off/template fallback works.
-   [ ] Abstention is a first-class state.
-   [ ] Analysis and dispatch are separated.
-   [ ] Approval is persisted, authorized, version-bound, and
    expiry-aware.
-   [ ] Duplicate/stale/rejected approval and dispatch attempts are
    safe.

## APIs, database, and UI

-   [ ] Database entities and API schemas agree.
-   [ ] API schemas and frontend types agree.
-   [ ] Identifiers, timestamps, units, CRS, enums, and nullability are
    consistent.
-   [ ] Migrations and constraints enforce intended state transitions.
-   [ ] Error envelopes, retries, timeouts, and idempotency are
    documented.
-   [ ] UI exposes source type, freshness, readiness, confidence, and
    abstention.
-   [ ] Every view refers to the same assessment and version
    identifiers.

## Testing, deployment, and operations

-   [ ] Unit, integration, geospatial, model, agent, API, security,
    frontend, and end-to-end tests exist where relevant.
-   [ ] Critical failure scenarios have automated tests.
-   [ ] Clean setup and demo reset work from a fresh checkout.
-   [ ] Logs trace one assessment end to end.
-   [ ] No secrets are committed.
-   [ ] Build and test results are reported honestly.
-   [ ] Known limitations and future dependencies are explicit.

------------------------------------------------------------------------

# 11. Recommended implementation order for the hackathon

Follow this sequence; do not attempt every production detail in
parallel.

1.  **Repository audit and clean startup.** Inspect existing files,
    install/build, run tests, verify environment variables and database
    startup.
2.  **End-to-end data contract.** Make one ward, one scenario, one
    assessment, and one API response work consistently.
3.  **Map and ward dashboard.** Show ward boundaries/risk, data source
    labels, timestamps, and quality state.
4.  **Deterministic scenario/simulator.** Add repeatable normal,
    rising-water, stale-sensor, and missing-data scenarios.
5.  **Risk calculation and explanation.** Produce reproducible risk
    classes and calculated evidence-backed explanations.
6.  **Forecast integration.** Use a real trained baseline only if data
    and evaluation are available; otherwise visibly label simulated
    forecast outputs.
7.  **Human review and simulated dispatch.** Persist approve/reject,
    bind the decision to the assessment, and prevent duplicate dispatch.
8.  **Routing or no-route behaviour.** Include only if the graph and
    edge attributes are sufficiently reliable; fail safely otherwise.
9.  **End-to-end hardening.** Run the core scenarios, test clean
    startup, fix visible errors, and rehearse the demo.
10. **Document deferred work.** Record remaining P0/P1 issues and do not
    claim they are solved unless verified.

**Time-box rule:** If a P0 operational safeguard cannot be completed
before the demo, disable the affected operational action and demonstrate
a clearly labelled simulation. Do not bypass the safeguard to make the
demo appear complete.

------------------------------------------------------------------------

# 12. Required output from Antigravity

Before declaring the prototype baseline ready, produce:

1.  **`GAP_AUDIT.md`** --- this register with statuses, evidence,
    owners/modules, and priority.
2.  **`REQUIREMENT_TEST_MATRIX.md`** --- requirement IDs mapped to code,
    tests, commands, and results.
3.  **`ARCHITECTURE_DECISIONS.md`** --- only new or changed decisions,
    with context, decision, trade-offs, and consequences.
4.  **`KNOWN_LIMITATIONS.md`** --- observed versus simulated data, model
    readiness, policy readiness, missing datasets, and unavailable
    operational capabilities.
5.  **A concise final audit report** --- what was changed, files
    changed, tests actually run, tests that failed, unresolved blockers,
    and the exact command to start the demo.

Do not create empty documents or mark all items complete to satisfy this
output requirement. Each report must reflect actual repository evidence.

## Final baseline rule

**F2 remains the canonical prototype guide unless an evidenced
contradiction requires a documented change.** This file is the
discrepancy and remediation register. Implement the smallest coherent,
testable end-to-end system first. Treat public-safety governance,
scientific honesty, reproducibility, and visible uncertainty as core
engineering requirements---not presentation polish.

A prototype that demonstrates a credible, explainable, reproducible
decision flow with honest limitations is stronger than a larger system
that appears sophisticated but cannot substantiate its predictions or
safety claims.


---

# Appendix A. Mandatory cross-document comparison matrix

Complete this matrix only after inspecting the relevant sections in **all four** documents. Add rows wherever one topic has multiple distinct decisions or formulas. `Same` is not enough: record section references and note any consequential difference.

| Topic | G1 section/reference | G2 section/reference | F1 section/reference | F2 section/reference | Canonical decision / discrepancy ID | Test/evidence |
|---|---|---|---|---|---|---|
| MVP scope and demo-complete | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Geographic AOI, wards and analytical grid | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Architecture and module boundaries | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Runtime topology, jobs and cadence | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Stack and version compatibility | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Dataset register, access and licenses | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Data zones, labels and provenance | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Database schema, constraints and roles | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| API contracts and error semantics | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| CRS, datum, units and spatial aggregation | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Hydrology equations and simulator | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Feature definitions and leakage controls | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| M1 susceptibility model | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| M2 forecast and quantile calibration | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| M3 hazard model and calibration | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Risk, exposure, vulnerability and confidence | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Explainability and evidence semantics | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Agent roster, permissions and contracts | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| LangGraph state, transitions and checkpointing | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| LLM grounding and fallback modes | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Abstention and insufficient evidence | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Human approval and dispatch controls | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Routing graph, costs and validity | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Frontend pages and state/error handling | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Security and authorization | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Observability and audit | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Testing and acceptance criteria | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| MLOps, promotion and rollback | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Docker/Compose and clean startup | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| Roadmap, dependencies and definition of done | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |
| MVP versus production boundaries | OPEN | OPEN | OPEN | OPEN | OPEN | OPEN |

`OPEN` is a placeholder, not a finding. Replace it with actual references and evidence; do not fill the matrix by guessing from headings.

# Appendix B. Required final Antigravity report

Before declaring the baseline ready, report:

1. Which four complete documents were read, and how full-document coverage was confirmed.
2. Total discrepancies found by priority and disposition.
3. The ten highest-risk open findings.
4. Every change made, with file paths.
5. Tests actually run, exact commands, pass/fail results and any skipped tests.
6. What is working end-to-end in the running prototype.
7. What is simulated, observed, derived, modelled, assumed, or locally validated.
8. Features intentionally disabled for demo safety.
9. Known residual gaps and why they remain.
10. A final decision: `BASELINE_READY_FOR_SIMULATED_PROTOTYPE`, `READY_WITH_DOCUMENTED_LIMITATIONS`, or `NOT_READY`, with evidence.

A passing documentation checklist is not a passing implementation. Never report success without executable evidence.
