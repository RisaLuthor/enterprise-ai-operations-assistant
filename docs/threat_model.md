# Threat Model (MVP)

## Primary risks
- Accidental inclusion of PII in logs or outputs
- Prompt injection causing unsafe tool use
- Overconfident outputs without assumptions
- Data leakage via verbose traces

## Mitigations (MVP)
- Redaction before logging
- Tool whitelist + explicit intent classification
- Structured plan format with assumptions required
- Minimal logging (opt-in verbose mode)

## Out of scope (MVP)
- Formal compliance frameworks
- External authentication/authorization
- Multi-tenant deployments