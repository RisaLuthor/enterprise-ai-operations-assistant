from __future__ import annotations

import os

from src.billing.square_client import create_subscription_checkout_link


def create_checkout_for_plan(email: str, plan: str) -> dict:
    success_url = os.getenv("APP_SUCCESS_URL", "http://127.0.0.1:8000/checkout/success")
    cancel_url = os.getenv("APP_CANCEL_URL", "http://127.0.0.1:8000/checkout/cancel")

    if plan == "enterprise":
        enterprise_url = os.getenv("SQUARE_ENTERPRISE_PAYMENT_LINK")
        if not enterprise_url:
            raise ValueError("SQUARE_ENTERPRISE_PAYMENT_LINK is not configured.")
        return {
            "checkout_url": enterprise_url,
            "plan": "enterprise",
            "mode": "manual",
        }

    result = create_subscription_checkout_link(
        email=email,
        plan=plan,
        success_url=success_url,
        cancel_url=cancel_url,
    )

    payment_link = result.get("payment_link", {})
    return {
        "checkout_url": payment_link.get("url"),
        "square_payment_link_id": payment_link.get("id"),
        "plan": plan,
        "mode": "hosted",
    }