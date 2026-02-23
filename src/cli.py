from __future__ import annotations

import argparse
from datetime import datetime

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

    # ✅ NEW: schema path for schema-aware SQL planning
    parser.add_argument("--schema", default=None, help="Path to a JSON schema file used for SQL planning")

    args = parser.parse_args(argv)

    user_text = " ".join(args.text).strip()
    if not user_text:
        print('Provide a request text. Example:\n  enterprise-ai-ops "Generate a SQL query to list active employees"')
        return 2

    # Governance-first: redact before logging
    redaction = redact_sensitive(user_text)

    # Route + plan
    route = route_intent(user_text)
    plan = build_plan(route, user_text)

    # Optional: SQL generation for QUERY intent
    sql_output = None
    if plan.intent == "QUERY":
        from .tools.sql_generator import generate_safe_sql

        # ✅ NEW: pass schema_path into generator
        sql_output = generate_safe_sql(user_text, schema_path=args.schema)

    # Print output
    if args.json:
        out = {"plan": plan.to_dict()}
        if sql_output:
            out["sql"] = {
                "dialect": getattr(sql_output, "dialect", "sqlserver"),
                "query": sql_output.query,
                "assumptions": sql_output.assumptions,
                "safety_notes": sql_output.safety_notes,
                "suggested_next_inputs": sql_output.suggested_next_inputs,
            }
        print(out)
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

        if sql_output:
            print("Generated SQL:")
            print(sql_output.query)

            print("\nSQL Assumptions:")
            for a in sql_output.assumptions:
                print(f"  - {a}")

            print("\nSafety Notes:")
            for note in sql_output.safety_notes:
                print(f"  - {note}")

            print("\nSuggested Next Inputs:")
            for n in sql_output.suggested_next_inputs:
                print(f"  - {n}")

    # Audit log (always logs the plan; includes SQL if generated)
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