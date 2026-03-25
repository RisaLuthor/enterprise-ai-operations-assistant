from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.audit.logger import AuditEvent, write_audit_event
from src.billing.checkout import create_checkout_for_plan
from src.billing.plans import PLANS
from src.billing.provisioning import apply_square_subscription_update, provision_user
from src.billing.square_webhooks import verify_square_webhook_signature
from src.core.auth import AuthContext, require_api_key
from src.core.errors import AppError, BadRequestError, app_error_handler, unhandled_error_handler
from src.db.init_db import init_db
from src.governance.redact import redact_sensitive
from src.planner import build_plan
from src.repositories.api_keys import get_api_key_for_user
from src.repositories.usage import get_monthly_usage_count, record_usage_event
from src.repositories.users import get_user_by_email
from src.router import route_intent
from src.tools.sql_generator import generate_safe_sql

APP_NAME = os.getenv("APP_NAME", "Enterprise AI Operations Assistant")
APP_ENV = os.getenv("APP_ENV", "dev")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=APP_NAME,
    summary="Governance-aware planning + schema-aware SQL drafting for enterprise workflows.",
    description=(
        "Enterprise-minded AI service that turns natural-language requests into reviewable, "
        "audit-friendly operational artifacts."
    ),
    version="1.5.0",
    contact={
        "name": "Risa Luthor (Luthor.Tech)",
        "url": "https://rmluthor.us",
    },
    license_info={"name": "MIT (or your preferred license)"},
    openapi_tags=[
        {"name": "Service", "description": "Service discovery and health monitoring endpoints."},
        {"name": "Planning", "description": "Structured planning and optional SQL drafting endpoints."},
        {"name": "SQL", "description": "Direct SQL drafting endpoints for product/API use."},
        {"name": "Billing", "description": "Checkout, provisioning, billing, pricing, and access endpoints."},
    ],
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    return await app_error_handler(request, exc)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return await unhandled_error_handler(request, exc)


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


class RootResponse(BaseModel):
    service: str
    docs: str
    health: str
    plan: str
    sql_generate: str
    checkout_start: str
    pricing: str
    access: str


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str


class PlanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    schema_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    audit: bool = Field(default=True)

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
    user_text: str = Field(..., min_length=3, max_length=2000)
    top_n: int = Field(default=100, ge=1, le=500)
    schema_name: Optional[str] = Field(default=None, min_length=1, max_length=100)

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


class ProvisionUserRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    plan: str = Field(..., min_length=3, max_length=50)
    square_customer_id: Optional[str] = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("A valid email address is required.")
        return cleaned

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, value: str) -> str:
        cleaned = value.strip().lower()
        allowed = {"individual", "company", "enterprise"}
        if cleaned not in allowed:
            raise ValueError(f"plan must be one of: {', '.join(sorted(allowed))}")
        return cleaned


class ProvisionUserResponse(BaseModel):
    user_id: int
    email: str
    plan: str
    api_key: str


class CheckoutStartRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    plan: str = Field(..., min_length=3, max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("A valid email address is required.")
        if cleaned.endswith("@example.com"):
            raise ValueError("Use a real email address for checkout testing.")
        return cleaned

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, value: str) -> str:
        cleaned = value.strip().lower()
        allowed = {"individual", "company", "enterprise"}
        if cleaned not in allowed:
            raise ValueError(f"plan must be one of: {', '.join(sorted(allowed))}")
        return cleaned


class CheckoutStartResponse(BaseModel):
    email: str
    plan: str
    checkout_url: str
    mode: str
    square_payment_link_id: Optional[str] = None


class AccessRetrieveRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("A valid email address is required.")
        return cleaned


class AccessRetrieveResponse(BaseModel):
    provisioned: bool
    email: str
    plan: Optional[str] = None
    api_key: Optional[str] = None


@app.api_route("/", methods=["GET", "HEAD"], response_model=RootResponse, tags=["Service"])
def root() -> RootResponse:
    return RootResponse(
        service="enterprise-ai-ops",
        docs="/docs",
        health="/health",
        plan="/plan",
        sql_generate="/v1/sql/generate",
        checkout_start="/v1/billing/checkout/start",
        pricing="/pricing",
        access="/access",
    )


@app.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["Service"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=APP_NAME, env=APP_ENV)


@app.api_route("/pricing", methods=["GET", "HEAD"], response_class=HTMLResponse, tags=["Billing"])
def pricing_page() -> HTMLResponse:
    pricing_path = Path(__file__).resolve().parent / "frontend" / "pricing.html"
    return HTMLResponse(pricing_path.read_text(encoding="utf-8"))


@app.api_route("/access", methods=["GET", "HEAD"], response_class=HTMLResponse, tags=["Billing"])
def access_page() -> HTMLResponse:
    access_path = Path(__file__).resolve().parent / "frontend" / "access.html"
    return HTMLResponse(access_path.read_text(encoding="utf-8"))


@app.post("/plan", response_model=PlanResponse, response_model_exclude_none=True, tags=["Planning"])
def plan_endpoint(req: PlanRequest, auth: AuthContext = Depends(require_api_key)) -> PlanResponse:
    user_text = req.text.strip()
    redaction = redact_sensitive(user_text)
    route = route_intent(user_text)
    plan = build_plan(route, user_text)

    sql_payload = None
    if plan.intent == "QUERY":
        sql_output = generate_safe_sql(user_text=user_text, schema_name=req.schema_name)
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


@app.post("/v1/sql/generate", response_model=SQLGenerateResponse, tags=["SQL"])
def generate_sql_endpoint(
    req: SQLGenerateRequest,
    auth: AuthContext = Depends(require_api_key),
) -> SQLGenerateResponse:
    plan_def = PLANS.get(auth.plan)
    if not plan_def:
        raise BadRequestError("Unknown plan configuration.")

    if req.top_n > plan_def.max_top_n:
        raise BadRequestError(f"{auth.plan.capitalize()} plan supports top_n up to {plan_def.max_top_n}.")

    current_usage = get_monthly_usage_count(auth.user_id)
    if plan_def.monthly_request_limit is not None and current_usage >= plan_def.monthly_request_limit:
        raise BadRequestError("Monthly request limit reached for this plan.")

    sql_output = generate_safe_sql(
        user_text=req.user_text,
        top_n=req.top_n,
        schema_name=req.schema_name,
    )

    if auth.user_id != 0:
        record_usage_event(auth.user_id, "/v1/sql/generate")

    risk_level = "LOW" if req.schema_name is not None else "MEDIUM"

    return SQLGenerateResponse(
        dialect=getattr(sql_output, "dialect", "sqlserver"),
        query=sql_output.query,
        assumptions=sql_output.assumptions,
        safety_notes=sql_output.safety_notes,
        suggested_next_inputs=sql_output.suggested_next_inputs,
        plan=auth.plan,
        risk_level=risk_level,
    )


@app.post("/v1/admin/provision-user", response_model=ProvisionUserResponse, tags=["Billing"])
def provision_user_endpoint(
    req: ProvisionUserRequest,
    auth: AuthContext = Depends(require_api_key),
) -> ProvisionUserResponse:
    if auth.plan != "enterprise":
        raise BadRequestError("Only enterprise/admin credentials can provision users.")

    result = provision_user(
        email=req.email.strip().lower(),
        plan=req.plan.strip().lower(),
        square_customer_id=req.square_customer_id,
    )
    return ProvisionUserResponse(**result)


@app.post("/v1/billing/checkout/start", response_model=CheckoutStartResponse, tags=["Billing"])
def checkout_start_endpoint(req: CheckoutStartRequest) -> CheckoutStartResponse:
    result = create_checkout_for_plan(email=req.email, plan=req.plan)
    return CheckoutStartResponse(
        email=req.email,
        plan=req.plan,
        checkout_url=result["checkout_url"],
        mode=result["mode"],
        square_payment_link_id=result.get("square_payment_link_id"),
    )


@app.post("/v1/access/retrieve", response_model=AccessRetrieveResponse, tags=["Billing"])
def access_retrieve_endpoint(req: AccessRetrieveRequest) -> AccessRetrieveResponse:
    user = get_user_by_email(req.email)
    if not user or not user.get("is_active"):
        return AccessRetrieveResponse(
            provisioned=False,
            email=req.email,
        )

    key_record = get_api_key_for_user(int(user["id"]))
    if not key_record or not key_record.get("is_active"):
        return AccessRetrieveResponse(
            provisioned=False,
            email=req.email,
            plan=user.get("plan"),
        )

    return AccessRetrieveResponse(
        provisioned=True,
        email=req.email,
        plan=user.get("plan"),
        api_key=key_record.get("api_key"),
    )


@app.get("/checkout/success", response_class=HTMLResponse, tags=["Billing"])
def checkout_success() -> HTMLResponse:
    return HTMLResponse(
        """
        <html>
          <head><title>Checkout Success</title></head>
          <body style="font-family: Arial, sans-serif; max-width: 720px; margin: 40px auto;">
            <h1>Payment received</h1>
            <p>Your checkout completed successfully.</p>
            <p>If your access has already been provisioned, you can retrieve it now.</p>
            <p><a href="/access">Go to access retrieval</a></p>
          </body>
        </html>
        """
    )


@app.get("/checkout/cancel", response_class=HTMLResponse, tags=["Billing"])
def checkout_cancel() -> HTMLResponse:
    return HTMLResponse(
        """
        <html>
          <head><title>Checkout Canceled</title></head>
          <body style="font-family: Arial, sans-serif; max-width: 720px; margin: 40px auto;">
            <h1>Checkout canceled</h1>
            <p>Your payment was not completed.</p>
            <p>You can go back and try again whenever you're ready.</p>
            <p><a href="/pricing">Return to pricing</a></p>
          </body>
        </html>
        """
    )


@app.post("/v1/billing/square/webhook", tags=["Billing"])
async def square_webhook_endpoint(
    request: Request,
    x_square_hmacsha256_signature: Optional[str] = Header(default=None),
):
    raw_body = (await request.body()).decode("utf-8")

    if not verify_square_webhook_signature(raw_body, x_square_hmacsha256_signature):
        return JSONResponse(status_code=403, content={"error": "invalid_signature"})

    payload = await request.json()
    event_type = payload.get("type")
    data_object = payload.get("data", {}).get("object", {})

    subscription = data_object.get("subscription", data_object)
    customer_id = subscription.get("customer_id")
    subscription_id = subscription.get("id")
    status = subscription.get("status")

    plan = None
    lowered = raw_body.lower()
    if "individual" in lowered:
        plan = "individual"
    elif "company" in lowered:
        plan = "company"
    elif "enterprise" in lowered:
        plan = "enterprise"

    if event_type:
        apply_square_subscription_update(
            customer_id=customer_id,
            subscription_id=subscription_id,
            status=status,
            plan=plan,
        )

    return {"received": True, "event_type": event_type}