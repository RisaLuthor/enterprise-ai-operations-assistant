from __future__ import annotations

import os

try:
    from square.utilities.webhooks_helper import is_valid_webhook_event_signature
except ImportError:
    is_valid_webhook_event_signature = None


SQUARE_WEBHOOK_SIGNATURE_KEY = os.getenv("SQUARE_WEBHOOK_SIGNATURE_KEY", "")
SQUARE_WEBHOOK_NOTIFICATION_URL = os.getenv("SQUARE_WEBHOOK_NOTIFICATION_URL", "")


def verify_square_webhook_signature(body: str, signature: str | None) -> bool:
    if not signature:
        return False
    if not SQUARE_WEBHOOK_SIGNATURE_KEY or not SQUARE_WEBHOOK_NOTIFICATION_URL:
        return False
    if is_valid_webhook_event_signature is None:
        return False

    return is_valid_webhook_event_signature(
        body,
        signature,
        SQUARE_WEBHOOK_SIGNATURE_KEY,
        SQUARE_WEBHOOK_NOTIFICATION_URL,
    )