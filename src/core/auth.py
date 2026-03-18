from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Header

from src.core.config import settings
from src.core.errors import UnauthorizedError
from src.repositories.api_keys import get_api_key_record


@dataclass(frozen=True)
class AuthContext:
    api_key: str
    plan: str
    user_id: int
    email: str


def resolve_plan_for_api_key(api_key: str) -> Optional[AuthContext]:
    record = get_api_key_record(api_key)
    if not record:
        return None

    if not record["is_active"] or not record["user_is_active"]:
        return None

    return AuthContext(
        api_key=record["api_key"],
        plan=record["plan"],
        user_id=int(record["user_id"]),
        email=record["email"],
    )


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> AuthContext:
    if not settings.require_api_key:
        return AuthContext(
            api_key="dev-bypass",
            plan="enterprise",
            user_id=0,
            email="dev@local",
        )

    if not x_api_key:
        raise UnauthorizedError("Missing X-API-Key header.")

    auth = resolve_plan_for_api_key(x_api_key)
    if not auth:
        raise UnauthorizedError("Invalid API key.")

    return auth