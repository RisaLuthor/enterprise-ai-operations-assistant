from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_sql_requires_api_key():
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