from __future__ import annotations

from src.db.init_db import init_db
from src.repositories.api_keys import create_api_key
from src.repositories.users import create_user, get_user_by_email


def seed() -> None:
    init_db()

    seed_users = [
        ("individual@example.com", "individual", "dev-individual-key"),
        ("company@example.com", "company", "dev-company-key"),
        ("enterprise@example.com", "enterprise", "dev-enterprise-key"),
    ]

    for email, plan, api_key in seed_users:
        existing = get_user_by_email(email)
        if existing:
            continue

        user_id = create_user(email=email, plan=plan)
        create_api_key(user_id=user_id, api_key=api_key)


if __name__ == "__main__":
    seed()
    print("Seeded development users and API keys.")