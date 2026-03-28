from fastapi import Header, HTTPException, status
from src.config import settings


def resolve_api_tier(x_api_key: str | None) -> str:
    if not settings.require_api_key:
        return "open"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )

    if x_api_key == settings.individual_api_key:
        return "individual"
    if x_api_key == settings.company_api_key:
        return "company"
    if x_api_key == settings.enterprise_api_key:
        return "enterprise"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key.",
    )


def get_api_tier(x_kieran_token: str | None = Header(default=None)) -> str:
    return resolve_api_tier(x_kieran_token)