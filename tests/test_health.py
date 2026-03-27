"""Basic health check test — runs without DB for CI."""
from fastapi.testclient import TestClient

def test_root():
    from app.main import app
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Financial Intelligence Processing System"
    assert data["status"] == "running"
