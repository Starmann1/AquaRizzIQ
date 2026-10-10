# ADR-005: LLM Abstraction with Strict Output Verifiers and Offline Modes

## Status
Accepted

## Context
LLMs provide flexible narrative synthesis for operator briefings, but present severe risks in emergency systems: hallucinated numbers, ungrounded instructions, network latency, and provider outages.

## Decision
AquaRizz supports three runtime modes via `LLM_MODE`:
1. `off`: Generates pure structured JSON.
2. `template` (Default): Evaluates deterministic Python f-string templates containing exact calculated metrics.
3. `llm`: Invokes an LLM provider adapter, passing ONLY structured facts.

When `LLM_MODE=llm`, the response is verified by automated safety rules (V1-V6):
- **V1 (Number Grounding)**: Rejects any numerical value not present in the input payload.
- **V2 (Evidence Citations)**: Rejects any cited evidence ID not in the active registry.
- **V3 (Length Constraint)**: Word count must be $\le 120$ words.
- **V4 (No Speculative Certainty)**: Bans absolute claims ("definitely", "guaranteed").
- **V5 (No Action Directives)**: Bans unapproved imperatives ("evacuate immediately").
- **V6 (Numerical Accuracy)**: Verifies that percentages match computed values within 1%.

If any verifier fails, the system automatically falls back to `template` output.
