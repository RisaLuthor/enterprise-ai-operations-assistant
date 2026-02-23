from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import sys

from .router import route_intent
from .planner import build_plan
from .governance.redact import redact_sensitive
from .audit.logger import AuditEvent, write_audit_event


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="enterprise-ai-ops",
        description="Enterprise AI Operations Assistant (MVP): intent routing + structured planning + audit logging.",
    )
    parser.add_argument("text", nargs="*", help="User request text")
    parser.add_argument("--no-audit", action="store_true", help="Disable writing audit logs")
    parser.add_argument("--audit-dir", default="audit", help="Directory to write audit logs")
    parser.add_argument("--json", action="store_true", help="Output plan as JSON-like dict")
    args = parser.parse_args(argv)

    user_text = " ".join(args.text).strip()
    if not user_text:
        print("Provide a request text. Example:\n  enterprise-ai-ops \"Generate a SQL query to list active employees\"")
        return 2

    # Governance-first: redact before logging
    redaction = redact_sensitive(user_text)

    # Route + plan
    route = route_intent(user_text)
    plan = build_plan(route, user_text)

    # Print output
    if args.json:
        print(plan.to_dict())
    else:
        print(f"\nIntent: {plan.intent} (confidence={plan.confidence:.2f})")
        if plan.risk_flags:
            print(f"Risk flags: {', '.join(plan.risk_flags)}")
        print("\nAssumptions:")
        for a in plan.assumptions:
            print(f"  - {a}")
        print("\nSteps:")
        for s in plan.steps:
            print(f"  - {s}")
        if plan.required_inputs:
            print("\nRequired inputs:")
            for ri in plan.required_inputs:
                print(f"  - {ri}")
        print(f"\nOutput format: {plan.output_format}\n")

    # Audit log
    if not args.no_audit:
        event_id = f"audit_{int(datetime.now().timestamp())}"
        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            redacted_input=redaction.redacted_text,
            route={"intent": route.intent.value, "confidence": route.confidence, "rationale": route.rationale},
            plan=plan.to_dict(),
            redaction_counts=redaction.redaction_counts,
        )
        path = write_audit_event(event, audit_dir=args.audit_dir)
        print(f"Audit log written: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())