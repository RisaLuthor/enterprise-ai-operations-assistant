from fastapi.testclient import TestClient

from src.api import app


def test_access_page_loads():
    with TestClient(app) as client:
        response = client.get("/access")
        assert response.status_code == 200
        assert "Retrieve your access" in response.text