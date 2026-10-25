import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from monitor.database import Base, register_endpoint, record_check_result
from monitor.analytics import calculate_percentiles, get_endpoint_analytics, generate_performance_insights


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    test_engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    monkeypatch.setattr("monitor.database.engine", test_engine)
    monkeypatch.setattr("monitor.database.SessionLocal", TestingSessionLocal)
    yield


def test_calculate_percentiles():
    data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p = calculate_percentiles(data, [50, 90, 95])
    assert p["p50"] == 60.0
    assert p["p90"] == 100.0


def test_endpoint_analytics_and_insights():
    ep = register_endpoint("Fast Service", "https://api.fast.com")
    
    # 5 successful checks with low latencies
    for lat in [100.0, 120.0, 110.0, 130.0, 115.0]:
        record_check_result(ep.id, status_code=200, response_time_ms=lat, is_success=True)

    stats = get_endpoint_analytics(ep.id, hours=1)
    assert stats["total_checks"] == 5
    assert stats["uptime_percentage"] == 100.0
    assert stats["avg_response_ms"] == 115.0
    assert stats["latest_status"] == "UP"

    insights = generate_performance_insights()
    assert len(insights) >= 1
    assert any(i["severity"] == "HEALTHY" for i in insights)
