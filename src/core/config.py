from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Enterprise AI Operations Assistant")
    env: str = os.getenv("APP_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    default_top_n: int = int(os.getenv("DEFAULT_TOP_N", "100"))
    max_top_n: int = int(os.getenv("MAX_TOP_N", "500"))
    require_api_key: bool = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"

    # Demo keys for now. Later these move to DB-backed storage.
    individual_api_key: str = os.getenv("INDIVIDUAL_API_KEY", "dev-individual-key")
    company_api_key: str = os.getenv("COMPANY_API_KEY", "dev-company-key")
    enterprise_api_key: str = os.getenv("ENTERPRISE_API_KEY", "dev-enterprise-key")


settings = Settings()