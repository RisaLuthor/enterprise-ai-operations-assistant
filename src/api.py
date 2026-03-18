from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from .router import route_intent
from .planner import build_plan
from .governance.redact import redact_sensitive
from .audit.logger import AuditEvent, write_audit_event
from .tools.sql_generator import generate_safe_sql


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

APP_NAME = os.getenv("APP_NAME", "Enterprise AI Operations Assistant")
APP_ENV = os.getenv("APP_ENV", "dev")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"

INDIVIDUAL_API_KEY = os.getenv("INDIVIDUAL_API_KEY", "dev-individual-key")
COMPANY_API_KEY = os.getenv("COMPANY_API_KEY", "dev-company-key")
ENTERPRISE_API_KEY = os.getenv("ENTERPRISE_API_KEY", "dev-enterprise-key")


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# App
# ------------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
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
        "- API-key-ready commercial usage model\n"
    ),
    version="1.1.0",
    contact={
        "name": "Risa Luthor (Luthor.Tech)",
        "url": "https://rmluthor.us",
    },
    license_info={"name": "MIT (or your preferred license)"},
    openapi_tags=[
        {"name": "Service", "description": "Service discovery and health monitoring endpoints."},
        {"name": "Planning", "description": "Structured planning and optional SQL drafting endpoints."},
        {"name": "SQL", "description": "Direct SQL drafting endpoints for product/API use."},
    ],
)


# ------------------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------------------

class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Invalid or missing API key.") -> None:
        super().__init__(code="unauthorized", message=message, status_code=401)


class BadRequestError(AppError):
    def __init__(self, message: str = "Invalid request.") -> None:
        super().__init__(code="bad_request", message=message, status_code=400)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
        },
    )


# ------------------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------------------

class AuthContext(BaseModel):
    api_key: str
    plan: str


def resolve_plan_for_api_key(api_key: str) -> Optional[str]:
    if api_key == INDIVIDUAL_API_KEY:
        return "individual"
    if api_key == COMPANY_API_KEY:
        return "company"
    if api_key == ENTERPRISE_API_KEY:
        return "enterprise"
    return None


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> AuthContext:
    if not REQUIRE_API_KEY:
        return AuthContext(api_key="dev-bypass", plan="enterprise")

    if not x_api_key:
        raise UnauthorizedError("Missing X-API-Key header.")

    plan = resolve_plan_for_api_key(x_api_key)
    if not plan:
        raise UnauthorizedError("Invalid API key.")

    return AuthContext(api_key=x_api_key, plan=plan)


# ------------------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------------------

@app.middleware("http")
async def add_service_headers_and_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    response.headers["X-Service-Name"] = "enterprise-ai-ops"

    logger.info(
        "request_complete path=%s method=%s status=%s duration_ms=%s",
        request.url.path,
        request.method,
        response.status_code,
        duration_ms,
    )
    return response


# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------

class RootResponse(BaseModel):
    service: str
    docs: str
    health: str
    plan: str
    sql_generate: str


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str


class PlanRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User request text (natural language).",
        examples=["Generate a SQL query to list active employees hired in the last 90 days"],
    )
    schema_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Optional approved schema name used to guide SQL drafting.",
        examples=["hr_demo"],
    )
    audit: bool = Field(
        default=True,
        description="If true, write an audit event to the audit log directory.",
        examples=[False],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must not be blank.")
        return cleaned


class PlanResponse(BaseModel):
    route: Dict[str, Any]
    plan: Dict[str, Any]
    sql: Optional[Dict[str, Any]] = None
    audit_id: Optional[str] = None
    requester_plan: Optional[str] = None


class SQLGenerateRequest(BaseModel):
    user_text: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language request for SQL drafting.",
        examples=["Show active employees hired in the last 90 days"],
    )
    top_n: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum rows to return in the draft SQL query.",
        examples=[25],
    )
    schema_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Optional approved schema name used to guide SQL drafting.",
        examples=["hr_demo"],
    )

    @field_validator("user_text")
    @classmethod
    def validate_user_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("user_text must not be blank.")
        return cleaned


class SQLGenerateResponse(BaseModel):
    dialect: str
    query: str
    assumptions: list[str]
    safety_notes: list[str]
    suggested_next_inputs: list[str]
    plan: str
    risk_level: str


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.api_route(
    "/",
    methods=["GET", "HEAD"],
    response_model=RootResponse,
    tags=["Service"],
    summary="Service discovery",
    description="Lightweight discovery endpoint for humans, tooling, and health dashboards.",
)
def root() -> RootResponse:
    return RootResponse(
        service="enterprise-ai-ops",
        docs="/docs",
        health="/health",
        plan="/plan",
        sql_generate="/v1/sql/generate",
    )


@app.api_route(
    "/health",
    methods=["GET", "HEAD"],
    response_model=HealthResponse,
    tags=["Service"],
    summary="Health check",
    description="Health check endpoint suitable for container orchestration and monitoring.",
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=APP_NAME,
        env=APP_ENV,
    )


@app.post(
    "/plan",
    response_model=PlanResponse,
    response_model_exclude_none=True,
    tags=["Planning"],
    summary="Generate a structured plan (and optional safe SQL draft)",
    description=(
        "Routes intent and returns a structured plan artifact (assumptions, steps, required inputs). "
        "If the intent is `QUERY`, returns a safe-by-default SQL draft guided by an optional approved schema name."
    ),
)
def plan_endpoint(
    req: PlanRequest,
    auth: AuthContext = Depends(require_api_key),
) -> PlanResponse:
    """
    Generate a governance-aware planning artifact.

    Workflow:
    1) Redact sensitive input before any logging
    2) Route intent deterministically
    3) Build a structured plan artifact
    4) If intent is QUERY, produce schema-aware SQL draft
    5) Optionally write an audit event (redacted input + plan + SQL)
    """
    user_text = req.text.strip()

    redaction = redact_sensitive(user_text)
    route = route_intent(user_text)
    plan = build_plan(route, user_text)

    sql_payload = None
    if plan.intent == "QUERY":
        sql_output = generate_safe_sql(
            user_text,
            schema_name=req.schema_name,
        )
        sql_payload = {
            "dialect": getattr(sql_output, "dialect", "sqlserver"),
            "query": sql_output.query,
            "assumptions": sql_output.assumptions,
            "safety_notes": sql_output.safety_notes,
            "suggested_next_inputs": sql_output.suggested_next_inputs,
        }

    audit_id = None
    if req.audit:
        audit_id = f"audit_{int(datetime.now().timestamp())}"
        event = AuditEvent(
            event_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            redacted_input=redaction.redacted_text,
            route={
                "intent": route.intent.value,
                "confidence": route.confidence,
                "rationale": route.rationale,
            },
            plan=plan.to_dict(),
            redaction_counts=redaction.redaction_counts,
            sql=sql_payload,
        )
        write_audit_event(event, audit_dir="audit")

    return PlanResponse(
        route={
            "intent": route.intent.value,
            "confidence": route.confidence,
            "rationale": route.rationale,
        },
        plan=plan.to_dict(),
        sql=sql_payload,
        audit_id=audit_id,
        requester_plan=auth.plan,
    )


@app.post(
    "/v1/sql/generate",
    response_model=SQLGenerateResponse,
    tags=["SQL"],
    summary="Generate safe draft SQL",
    description="Direct SQL drafting endpoint for product/API use with plan-aware limits.",
)
def generate_sql_endpoint(
    req: SQLGenerateRequest,
    auth: AuthContext = Depends(require_api_key),
) -> SQLGenerateResponse:
    logger.info(
        "sql_generate_requested plan=%s schema_name=%s top_n=%s",
        auth.plan,
        req.schema_name,
        req.top_n,
    )

    if auth.plan == "individual" and req.top_n > 100:
        raise BadRequestError("Individual plan supports top_n up to 100.")

    if auth.plan == "company" and req.top_n > 250:
        raise BadRequestError("Company plan supports top_n up to 250.")

    sql_output = generate_safe_sql(
        user_text=req.user_text,
        top_n=req.top_n,
        schema_name=req.schema_name,
    )

    risk_level = "LOW"
    if req.schema_name is None:
        risk_level = "MEDIUM"

    return SQLGenerateResponse(
        dialect=getattr(sql_output, "dialect", "sqlserver"),
        query=sql_output.query,
        assumptions=sql_output.assumptions,
        safety_notes=sql_output.safety_notes,
        suggested_next_inputs=sql_output.suggested_next_inputs,
        plan=auth.plan,
        risk_level=risk_level,
    )