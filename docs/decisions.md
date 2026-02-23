# Architecture Decisions

## ADR-001: Start with a CLI-first MVP
**Decision:** MVP ships as a CLI before any web UI.  
**Why:** Fast iteration, easy demos, low dependency risk, clean audit traces.

## ADR-002: Produce plans, not just answers
**Decision:** Assistant outputs a structured plan + assumptions.  
**Why:** Enterprise reviewers care about traceability and predictable behavior.

## ADR-003: Governance-first logging
**Decision:** Store only redacted inputs and structured outputs in logs.  
**Why:** Demonstrates enterprise-safe design patterns and reduces risk.

## ADR-004: Tool whitelist for execution
**Decision:** Only allow explicit, whitelisted actions.  
**Why:** Prevents unsafe or unbounded behavior and improves auditability.