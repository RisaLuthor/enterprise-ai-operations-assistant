from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanDefinition:
    name: str
    max_top_n: int
    monthly_request_limit: int | None


PLANS = {
    "individual": PlanDefinition(
        name="individual",
        max_top_n=100,
        monthly_request_limit=1000,
    ),
    "company": PlanDefinition(
        name="company",
        max_top_n=250,
        monthly_request_limit=10000,
    ),
    "enterprise": PlanDefinition(
        name="enterprise",
        max_top_n=500,
        monthly_request_limit=None,
    ),
}