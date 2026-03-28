import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


APP_ENV = os.getenv("APP_ENV", "dev").strip().lower()


def _required(name: str, *, test_default: str | None = None) -> str:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()

    if APP_ENV == "test" and test_default is not None:
        return test_default

    raise ValueError(f"Missing required environment variable: {name}")


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

    individual_api_key=_required("INDIVIDUAL_API_KEY", test_default="test-individual-key"),
    company_api_key=_required("COMPANY_API_KEY", test_default="test-company-key"),
    enterprise_api_key=_required("ENTERPRISE_API_KEY", test_default="test-enterprise-key"),

    square_access_token=_required("SQUARE_ACCESS_TOKEN", test_default="test-square-token"),
    square_environment=os.getenv("SQUARE_ENVIRONMENT", "sandbox"),
    square_location_id=_required("SQUARE_LOCATION_ID", test_default="test-location-id"),
    square_webhook_signature_key=_required("SQUARE_WEBHOOK_SIGNATURE_KEY", test_default="test-webhook-signature"),
    square_webhook_notification_url=_required(
        "SQUARE_WEBHOOK_NOTIFICATION_URL",
        test_default="https://example.com/v1/billing/square/webhook",
    ),

    square_individual_plan_variation_id=_required(
        "SQUARE_INDIVIDUAL_PLAN_VARIATION_ID",
        test_default="test-individual-plan",
    ),
    square_company_plan_variation_id=_required(
        "SQUARE_COMPANY_PLAN_VARIATION_ID",
        test_default="test-company-plan",
    ),
    square_enterprise_payment_link=_required(
        "SQUARE_ENTERPRISE_PAYMENT_LINK",
        test_default="https://example.com/enterprise",
    ),

    app_success_url=_required(
        "APP_SUCCESS_URL",
        test_default="http://127.0.0.1:8000/checkout/success",
    ),
    app_cancel_url=_required(
        "APP_CANCEL_URL",
        test_default="http://127.0.0.1:8000/checkout/cancel",
    ),
)