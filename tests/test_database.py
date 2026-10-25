import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from monitor.database import (
    Base,
    Endpoint,
    MetricCheck,
    register_endpoint,
    record_check_result,
    get_db_session
)


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    test_engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    monkeypatch.setattr("monitor.database.engine", test_engine)
    monkeypatch.setattr("monitor.database.SessionLocal", TestingSessionLocal)
    yield


def test_register_and_update_endpoint():
    ep = register_endpoint("Test Service", "https://api.test.com/v1", method="GET", expected_status=200)
    assert ep.id is not None
    assert ep.name == "Test Service"
    assert ep.url == "https://api.test.com/v1"

    # Test update existing endpoint
    ep_updated = register_endpoint("Updated Service", "https://api.test.com/v1", method="POST", expected_status=201)
    assert ep_updated.id == ep.id
    assert ep_updated.name == "Updated Service"
    assert ep_updated.method == "POST"
    assert ep_updated.expected_status == 201


def test_record_metric_check():
    ep = register_endpoint("Echo API", "https://api.test.com/echo")
    check = record_check_result(
        endpoint_id=ep.id,
        status_code=200,
        response_time_ms=124.5,
        is_success=True,
        dns_time_ms=15.0,
        ttfb_ms=65.2
    )

    assert check.id is not None
    assert check.status_code == 200
    assert check.response_time_ms == 124.5
    assert check.is_success is True

    with get_db_session() as session:
        stored = session.query(MetricCheck).filter(MetricCheck.id == check.id).first()
        assert stored.endpoint_id == ep.id
        assert stored.dns_time_ms == 15.0
