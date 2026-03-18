from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Header

from src.core.config import settings
from src.core.errors import UnauthorizedError


@dataclass(frozen=True)
class AuthContext:
    api_key: str
    plan: str


def resolve_plan_for_api_key(api_key: str) -> Optional[str]:
    if api_key == settings.individual_api_key:
        return "individual"
    if api_key == settings.company_api_key:
        return "company"
    if api_key == settings.enterprise_api_key:
        return "enterprise"
    return None


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> AuthContext:
    if not settings.require_api_key:
        return AuthContext(api_key="dev-bypass", plan="enterprise")

    if not x_api_key:
        raise UnauthorizedError("Missing X-API-Key header.")

    plan = resolve_plan_for_api_key(x_api_key)
    if not plan:
        raise UnauthorizedError("Invalid API key.")

    return AuthContext(api_key=x_api_key, plan=plan)