from __future__ import annotations

import secrets

from src.repositories.api_keys import create_api_key, get_api_key_for_user
from src.repositories.users import (
    create_user,
    get_user_by_email,
    get_user_by_square_customer_id,
    set_user_active,
    update_user_plan,
    update_user_square_subscription,
)


def generate_api_key() -> str:
    return f"eaoa_{secrets.token_urlsafe(24)}"


def provision_user(email: str, plan: str, square_customer_id: str | None = None) -> dict:
    existing = get_user_by_email(email)
    if existing:
        update_user_plan(existing["id"], plan)

        key_record = get_api_key_for_user(existing["id"])
        if key_record:
            return {
                "user_id": existing["id"],
                "email": existing["email"],
                "plan": plan,
                "api_key": key_record["api_key"],
            }

        api_key = generate_api_key()
        create_api_key(existing["id"], api_key)
        return {
            "user_id": existing["id"],
            "email": existing["email"],
            "plan": plan,
            "api_key": api_key,
        }

    user_id = create_user(email=email, plan=plan, square_customer_id=square_customer_id)
    api_key = generate_api_key()
    create_api_key(user_id, api_key)
    return {
        "user_id": user_id,
        "email": email,
        "plan": plan,
        "api_key": api_key,
    }


def apply_square_subscription_update(
    *,
    customer_id: str | None,
    subscription_id: str | None,
    status: str | None,
    plan: str | None = None,
) -> None:
    if not customer_id:
        return

    user = get_user_by_square_customer_id(customer_id)
    if not user:
        return

    if subscription_id:
        update_user_square_subscription(user["id"], subscription_id)

    if plan:
        update_user_plan(user["id"], plan)

    normalized = (status or "").upper()
    if normalized in {"ACTIVE", "PENDING"}:
        set_user_active(user["id"], True)
    elif normalized in {"CANCELED", "PAUSED", "DEACTIVATED"}:
        set_user_active(user["id"], False)