import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    log_level: str
    require_api_key: bool
    app_db_path: str

    individual_api_key: str
    company_api_key: str
    enterprise_api_key: str

    square_access_token: str
    square_environment: str
    square_location_id: str
    square_webhook_signature_key: str
    square_webhook_notification_url: str

    square_individual_plan_variation_id: str
    square_company_plan_variation_id: str
    square_enterprise_payment_link: str

    app_success_url: str
    app_cancel_url: str

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() == "dev"

    @property
    def square_base_url(self) -> str:
        if self.square_environment.lower() == "production":
            return "https://connect.squareup.com"
        return "https://connect.squareupsandbox.com"


settings = Settings(
    app_name=os.getenv("APP_NAME", "Enterprise AI Operations Assistant"),
    app_env=os.getenv("APP_ENV", "dev"),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    require_api_key=_as_bool(os.getenv("REQUIRE_API_KEY"), default=True),
    app_db_path=os.getenv("APP_DB_PATH", "data/app.db"),

    individual_api_key=_required("INDIVIDUAL_API_KEY"),
    company_api_key=_required("COMPANY_API_KEY"),
    enterprise_api_key=_required("ENTERPRISE_API_KEY"),

    square_access_token=_required("SQUARE_ACCESS_TOKEN"),
    square_environment=os.getenv("SQUARE_ENVIRONMENT", "sandbox"),
    square_location_id=_required("SQUARE_LOCATION_ID"),
    square_webhook_signature_key=_required("SQUARE_WEBHOOK_SIGNATURE_KEY"),
    square_webhook_notification_url=_required("SQUARE_WEBHOOK_NOTIFICATION_URL"),

    square_individual_plan_variation_id=_required("SQUARE_INDIVIDUAL_PLAN_VARIATION_ID"),
    square_company_plan_variation_id=_required("SQUARE_COMPANY_PLAN_VARIATION_ID"),
    square_enterprise_payment_link=_required("SQUARE_ENTERPRISE_PAYMENT_LINK"),

    app_success_url=_required("APP_SUCCESS_URL"),
    app_cancel_url=_required("APP_CANCEL_URL"),
)