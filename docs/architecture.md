# Architecture

## Goal
Provide an enterprise-minded AI assistant that converts natural language requests into **structured, auditable actions** (plans, queries, validations) with governance-aware guardrails.

## Core flow (MVP)
User request
→ Intent Router (classifies request type)
→ Planner (creates structured plan + assumptions)
→ Executor (runs allowed tools/actions)
→ Response Composer (formats output + trace)

## Components
### Intent Router
Classifies user input into one of:
- `QUERY` (generate SQL plan + safe query)
- `VALIDATE` (check rules/constraints, flag risks)
- `SUMMARIZE` (summarize structured content)
- `EXPLAIN` (explain business logic / decisions)

### Planner
Outputs a structured plan:
- intent
- assumptions
- steps
- required inputs
- risk flags (PII, unsafe actions, missing context)

### Executor
Runs only whitelisted actions:
- `generate_sql` (no execution in MVP)
- `validate_rules` (static rule checks)
- `summarize_text` (deterministic summary in MVP)

### Governance
- Do not store raw sensitive data by default
- Redact common PII patterns before logging
- Emit an audit trace with each response

## Interfaces (MVP)
- CLI entrypoint
- Local JSON audit log
- Example inputs in `/examples`

## Non-goals (MVP)
- Connecting to live enterprise databases
- Autonomous actions without explicit user confirmation
- Storing full conversations as-is