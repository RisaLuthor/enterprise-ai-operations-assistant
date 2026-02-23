from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .router import Intent, RouteResult


@dataclass
class Plan:
    plan_id: str
    created_at: str
    intent: str
    confidence: float
    assumptions: List[str]
    steps: List[str]
    required_inputs: List[str]
    risk_flags: List[str]
    output_format: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_plan(route: RouteResult, user_text: str) -> Plan:
    """
    Produces an auditable plan (not just an answer). This is a core enterprise signal.
    """
    now = datetime.now(timezone.utc).isoformat()
    plan_id = f"plan_{int(datetime.now().timestamp())}"

    assumptions: List[str] = []
    steps: List[str] = []
    required_inputs: List[str] = []
    risk_flags: List[str] = []

    # Very lightweight risk heuristics (MVP)
    lowered = (user_text or "").lower()
    if any(k in lowered for k in ["ssn", "social security", "password", "dob", "date of birth"]):
        risk_flags.append("POTENTIAL_PII")

    if route.intent == Intent.QUERY:
        assumptions = [
            "User intends to generate a SQL query plan (not execute it).",
            "Target schema/tables are not provided yet.",
            "Output should be safe-by-default (read-only).",
        ]
        required_inputs = [
            "Database type (e.g., SQL Server, Postgres, Oracle)",
            "Table names and key columns",
            "Desired filters and timeframe",
        ]
        steps = [
            "Confirm data source and schema constraints.",
            "Draft a read-only SQL query with explicit joins/filters.",
            "Add guardrails (limit rows, avoid sensitive columns).",
            "Return query + explanation + assumptions.",
        ]
        output_format = "sql_plan"

    elif route.intent == Intent.VALIDATE:
        assumptions = [
            "User wants to validate business rules or constraints.",
            "System context may be partial; clarify missing inputs.",
        ]
        required_inputs = [
            "Rules/constraints in a structured form (or examples)",
            "Edge cases or known failures (if any)",
        ]
        steps = [
            "Extract rules and define them in a consistent schema.",
            "Check for contradictions and missing branches.",
            "Propose targeted test cases for risk areas.",
            "Return a structured risk report + next actions.",
        ]
        output_format = "validation_report"

    elif route.intent == Intent.SUMMARIZE:
        assumptions = [
            "User wants a concise summary faithful to the input content.",
            "No external facts will be introduced.",
        ]
        required_inputs = ["Text to summarize", "Preferred length (optional)"]
        steps = [
            "Identify key points and outcomes.",
            "Condense into a clear, structured summary.",
            "Return summary with optional bullet highlights.",
        ]
        output_format = "summary"

    else:  # EXPLAIN / UNKNOWN
        assumptions = [
            "User wants an explanation or reasoning-oriented response.",
            "We will state assumptions explicitly when context is missing.",
        ]
        required_inputs = ["Any relevant context or constraints (optional)"]
        steps = [
            "Clarify the goal and constraints.",
            "Explain the concept with concrete examples.",
            "Provide next-step actions or checks.",
        ]
        output_format = "explanation"

    return Plan(
        plan_id=plan_id,
        created_at=now,
        intent=route.intent.value,
        confidence=route.confidence,
        assumptions=assumptions,
        steps=steps,
        required_inputs=required_inputs,
        risk_flags=risk_flags,
        output_format=output_format,
    )