import pytest
from app import app
from monitor.database import init_db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as client:
        yield client


def test_api_endpoints_list(client):
    res = client.get("/api/endpoints")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)


def test_api_add_endpoint(client):
    payload = {
        "name": "Integration Test API",
        "url": "https://httpbin.org/get",
        "method": "GET",
        "expected_status": 200,
        "interval_seconds": 60
    }
    res = client.post("/api/endpoints", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert "endpoint" in data
    assert data["endpoint"]["name"] == "Integration Test API"


def test_prometheus_metrics_endpoint(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "api_response_time_ms" in res.text
    assert "api_uptime_status" in res.text
