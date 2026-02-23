from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


@dataclass(frozen=True)
class RedactionResult:
    redacted_text: str
    redaction_counts: Dict[str, int]


def redact_sensitive(text: str) -> RedactionResult:
    """
    Basic redaction for MVP. Keeps logs safer by default.
    """
    counts = {"email": 0, "phone": 0, "ssn": 0}
    out = text or ""

    out, n = _EMAIL_RE.subn("[REDACTED_EMAIL]", out)
    counts["email"] += n

    out, n = _PHONE_RE.subn("[REDACTED_PHONE]", out)
    counts["phone"] += n

    out, n = _SSN_RE.subn("[REDACTED_SSN]", out)
    counts["ssn"] += n

    return RedactionResult(out, counts)