from fastapi.testclient import TestClient

from src.api import app
from src.db.seed_dev_data import seed


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_generate_sql_requires_api_key():
    with TestClient(app) as client:
        response = client.post(
            "/v1/sql/generate",
            json={
                "user_text": "Show active employees",
                "top_n": 25,
                "schema_name": "hr_demo",
            },
        )
        assert response.status_code == 401


def test_generate_sql_with_valid_api_key():
    seed()
    with TestClient(app) as client:
        response = client.post(
            "/v1/sql/generate",
            headers={"X-API-Key": "dev-individual-key"},
            json={
                "user_text": "Show active employees from the last 90 days",
                "top_n": 25,
                "schema_name": "hr_demo",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["dialect"] == "sqlserver"
        assert body["plan"] == "individual"
        assert "SELECT TOP (25)" in body["query"]


def test_individual_plan_limit_enforced():
    seed()
    with TestClient(app) as client:
        response = client.post(
            "/v1/sql/generate",
            headers={"X-API-Key": "dev-individual-key"},
            json={
                "user_text": "Show active employees",
                "top_n": 101,
                "schema_name": "hr_demo",
            },
        )
        assert response.status_code == 400


def test_company_plan_limit_enforced():
    seed()
    with TestClient(app) as client:
        response = client.post(
            "/v1/sql/generate",
            headers={"X-API-Key": "dev-company-key"},
            json={
                "user_text": "Show active employees",
                "top_n": 251,
                "schema_name": "hr_demo",
            },
        )
        assert response.status_code == 400