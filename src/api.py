from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from .router import route_intent
from .planner import build_plan
from .governance.redact import redact_sensitive
from .audit.logger import AuditEvent, write_audit_event
from .tools.sql_generator import generate_safe_sql


app = FastAPI(
    title="Enterprise AI Operations Assistant",
    summary="Governance-aware planning + schema-aware SQL drafting for enterprise workflows.",
    description=(
        "Enterprise-minded AI service that turns natural-language requests into reviewable, "
        "audit-friendly operational artifacts.\n\n"
        "**Key capabilities**:\n"
        "- Intent routing (deterministic)\n"
        "- Structured plan generation (assumptions/steps/required inputs)\n"
        "- Governance-first redaction\n"
        "- Optional audit logging\n"
        "- Schema-aware SQL drafting (safe-by-default)\n"
    ),
    version="1.0.0",
    contact={
        "name": "Risa Luthor (Luthor.Tech)",
        "url": "https://rmluthor.us",
    },
    license_info={"name": "MIT (or your preferred license)"},
    openapi_tags=[
        {"name": "Service", "description": "Service discovery and health monitoring endpoints."},
        {"name": "Planning", "description": "Structured planning and optional SQL drafting endpoints."},
    ],
)


# Optional: a tiny middleware that adds a helpful header for debugging / demos.
@app.middleware("http")
async def add_service_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Service-Name"] = "enterprise-ai-ops"
    return response


class RootResponse(BaseModel):
    service: str
    docs: str
    health: str
    plan: str


class HealthResponse(BaseModel):
    status: str


class PlanRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="User request text (natural language).",
        examples=["Generate a SQL query to list active employees hired in the last 90 days"],
    )
    schema_path: Optional[str] = Field(
        default=None,
        description="Optional path to a JSON schema file used to guide SQL drafting.",
        examples=["examples/schema_ps.json"],
    )
    audit: bool = Field(
        default=True,
        description="If true, write an audit event to the audit log directory.",
        examples=[False],
    )


class PlanResponse(BaseModel):
    route: Dict[str, Any]
    plan: Dict[str, Any]
    sql: Optional[Dict[str, Any]] = None
    audit_id: Optional[str] = None


# IMPORTANT CHANGE:
# Use api_route to support both GET and HEAD. This prevents 405 on `curl -I` and some proxies.
@app.api_route(
    "/",
    methods=["GET", "HEAD"],
    response_model=RootResponse,
    tags=["Service"],
    summary="Service discovery",
    description="Lightweight discovery endpoint for humans, tooling, and health dashboards.",
)
def root() -> RootResponse:
    """Service discovery endpoint (prevents `/` from returning 404 in demos)."""
    return RootResponse(
        service="enterprise-ai-ops",
        docs="/docs",
        health="/health",
        plan="/plan",
    )


# IMPORTANT CHANGE:
# Support HEAD here too.
@app.api_route(
    "/health",
    methods=["GET", "HEAD"],
    response_model=HealthResponse,
    tags=["Service"],
    summary="Health check",
    description="Health check endpoint suitable for container orchestration and monitoring.",
)
def health() -> HealthResponse:
    """Health check endpoint for orchestration (Kubernetes, ECS, etc.)."""
    return HealthResponse(status="ok")


@app.post(
    "/plan",
    response_model=PlanResponse,
    response_model_exclude_none=True,
    tags=["Planning"],
    summary="Generate a structured plan (and optional safe SQL draft)",
    description=(
        "Routes intent and returns a structured plan artifact (assumptions, steps, required inputs). "
        "If the intent is `QUERY`, returns a safe-by-default SQL draft guided by an optional schema file."
    ),
)
def plan_endpoint(req: PlanRequest) -> PlanResponse:
    """
    Generate a governance-aware planning artifact.

    Workflow:
    1) Redact sensitive input before any logging
    2) Route intent deterministically
    3) Build a structured plan artifact
    4) If intent is QUERY, produce schema-aware SQL draft
    5) Optionally write an audit event (redacted input + plan + SQL)
    """
    user_text = (req.text or "").strip()

    # Governance-first: redact before logging or audit persistence
    redaction = redact_sensitive(user_text)

    # Route + plan
    route = route_intent(user_text)
    plan = build_plan(route, user_text)

    # Optional: SQL generation for QUERY intent
    sql_payload = None
    if plan.intent == "QUERY":
        sql_output = generate_safe_sql(user_text, schema_path=req.schema_path)
        sql_payload = {
            "dialect": getattr(sql_output, "dialect", "sqlserver"),
            "query": sql_output.query,
            "assumptions": sql_output.assumptions,
            "safety_notes": sql_output.safety_notes,
            "suggested_next_inputs": sql_output.suggested_next_inputs,
        }

    # Optional: audit log
    audit_id = None
    if req.audit:
        audit_id = f"audit_{int(datetime.now().timestamp())}"
        event = AuditEvent(
            event_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            redacted_input=redaction.redacted_text,
            route={"intent": route.intent.value, "confidence": route.confidence, "rationale": route.rationale},
            plan=plan.to_dict(),
            redaction_counts=redaction.redaction_counts,
            sql=sql_payload,
        )
        write_audit_event(event, audit_dir="audit")

    return PlanResponse(
        route={"intent": route.intent.value, "confidence": route.confidence, "rationale": route.rationale},
        plan=plan.to_dict(),
        sql=sql_payload,
        audit_id=audit_id,
    )