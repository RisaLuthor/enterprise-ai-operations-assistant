from __future__ import annotations

import os
import secrets
from typing import Optional

import httpx


def get_square_base_url() -> str:
    environment_name = os.getenv("SQUARE_ENVIRONMENT", "sandbox").lower()
    if environment_name == "sandbox":
        return "https://connect.squareupsandbox.com"
    return "https://connect.squareup.com"


def get_square_access_token() -> str:
    token = os.getenv("SQUARE_ACCESS_TOKEN", "")
    if not token:
        raise ValueError("SQUARE_ACCESS_TOKEN is not configured.")
    return token


def get_plan_variation_id(plan: str) -> Optional[str]:
    mapping = {
        "individual": os.getenv("SQUARE_INDIVIDUAL_PLAN_VARIATION_ID"),
        "company": os.getenv("SQUARE_COMPANY_PLAN_VARIATION_ID"),
        "enterprise": None,
    }
    return mapping.get(plan)


def get_plan_amount(plan: str) -> int:
    pricing = {
        "individual": 900,   # $9.00
        "company": 4900,     # $49.00
    }
    amount = pricing.get(plan)
    if amount is None:
        raise ValueError(f"No amount configured for plan '{plan}'.")
    return amount


def create_subscription_checkout_link(
    *,
    email: str,
    plan: str,
    success_url: str,
    cancel_url: str,  # reserved for later if you want separate UX
) -> dict:
    plan_variation_id = get_plan_variation_id(plan)
    if not plan_variation_id:
        raise ValueError(f"No Square subscription plan variation configured for plan '{plan}'.")

    location_id = os.getenv("SQUARE_LOCATION_ID", "")
    if not location_id:
        raise ValueError("SQUARE_LOCATION_ID is not configured.")

    body = {
        "idempotency_key": secrets.token_hex(16),
        "quick_pay": {
            "name": f"Enterprise AI Operations Assistant - {plan.capitalize()}",
            "price_money": {
                "amount": get_plan_amount(plan),
                "currency": "USD",
            },
            "location_id": location_id,
        },
        "checkout_options": {
            "redirect_url": success_url,
            "merchant_support_email": email,
        },
        "pre_populated_data": {
            "buyer_email": email,
        },
        # Square docs call this subscription_plan_id, and the value should be the
        # subscription plan VARIATION id you copied from Square.
        "subscription_plan_id": plan_variation_id,
    }

    response = httpx.post(
        f"{get_square_base_url()}/v2/online-checkout/payment-links",
        headers={
            "Authorization": f"Bearer {get_square_access_token()}",
            "Content-Type": "application/json",
            "Square-Version": "2026-01-22",
        },
        json=body,
        timeout=30.0,
    )

    if response.status_code >= 400:
        raise ValueError(f"Square API error {response.status_code}: {response.text}")

    data = response.json()
    payment_link = data.get("payment_link")
    if not payment_link:
        raise ValueError(f"Square response missing payment_link: {data}")

    return {
        "payment_link": {
            "id": payment_link.get("id"),
            "url": payment_link.get("url"),
        }
    }