from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Intent(str, Enum):
    QUERY = "QUERY"
    VALIDATE = "VALIDATE"
    SUMMARIZE = "SUMMARIZE"
    EXPLAIN = "EXPLAIN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RouteResult:
    intent: Intent
    confidence: float
    rationale: str


def route_intent(user_text: str) -> RouteResult:
    """
    Lightweight, deterministic router for the MVP.
    We keep it simple and auditable. This can later be replaced with an LLM router.
    """
    text = (user_text or "").strip().lower()
    if not text:
        return RouteResult(Intent.UNKNOWN, 0.0, "Empty input")

    query_terms = ("select", "sql", "query", "report", "table", "join", "where", "count", "list")
    validate_terms = ("validate", "check", "verify", "rule", "constraint", "policy", "compliance", "edge case")
    summarize_terms = ("summarize", "summary", "tl;dr", "recap", "shorten")
    explain_terms = ("explain", "why", "how", "walk me through", "reason", "rationale")

    # Simple scoring
    score = {Intent.QUERY: 0, Intent.VALIDATE: 0, Intent.SUMMARIZE: 0, Intent.EXPLAIN: 0}
    for t in query_terms:
        if t in text:
            score[Intent.QUERY] += 1
    for t in validate_terms:
        if t in text:
            score[Intent.VALIDATE] += 1
    for t in summarize_terms:
        if t in text:
            score[Intent.SUMMARIZE] += 1
    for t in explain_terms:
        if t in text:
            score[Intent.EXPLAIN] += 1

    best_intent = max(score, key=score.get)
    best_score = score[best_intent]

    if best_score == 0:
        # Default behavior: EXPLAIN is usually safest for generic prompts
        return RouteResult(Intent.EXPLAIN, 0.35, "No explicit keywords matched; defaulting to EXPLAIN")

    # Confidence is simple normalization for MVP
    confidence = min(0.95, 0.45 + (best_score * 0.15))
    return RouteResult(best_intent, confidence, f"Matched keywords for {best_intent.value}")