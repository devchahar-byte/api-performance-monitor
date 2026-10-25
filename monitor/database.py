import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import config

Base = declarative_base()


class Endpoint(Base):
    """Monitored API endpoint definition."""
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True, index=True)
    method = Column(String(10), default="GET")
    headers_json = Column(Text, nullable=True)
    expected_status = Column(Integer, default=200)
    interval_seconds = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    metrics = relationship("MetricCheck", back_populates="endpoint", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "method": self.method,
            "expected_status": self.expected_status,
            "interval_seconds": self.interval_seconds,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MetricCheck(Base):
    """Single execution probe result for an API endpoint."""
    __tablename__ = "metric_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False, index=True)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=False)
    dns_time_ms = Column(Float, nullable=True)
    ttfb_ms = Column(Float, nullable=True)
    is_success = Column(Boolean, default=True)
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    content_length = Column(Integer, nullable=True)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    endpoint = relationship("Endpoint", back_populates="metrics")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "endpoint_name": self.endpoint.name if self.endpoint else None,
            "endpoint_url": self.endpoint.url if self.endpoint else None,
            "status_code": self.status_code,
            "response_time_ms": round(self.response_time_ms, 2) if self.response_time_ms is not None else None,
            "dns_time_ms": round(self.dns_time_ms, 2) if self.dns_time_ms is not None else None,
            "ttfb_ms": round(self.ttfb_ms, 2) if self.ttfb_ms is not None else None,
            "is_success": self.is_success,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "content_length": self.content_length,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


# Database engine & session
engine = create_engine(config.DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(custom_engine=None) -> None:
    """Initialize database tables and seed default endpoints if empty."""
    target_engine = custom_engine or engine
    Base.metadata.create_all(bind=target_engine)

    with Session(target_engine) as session:
        count = session.query(Endpoint).count()
        if count == 0:
            for ep_data in config.DEFAULT_ENDPOINTS:
                ep = Endpoint(
                    name=ep_data["name"],
                    url=ep_data["url"],
                    method=ep_data.get("method", "GET"),
                    expected_status=ep_data.get("expected_status", 200),
                    interval_seconds=ep_data.get("interval_seconds", 60),
                    is_active=True
                )
                session.add(ep)
            session.commit()


def get_db_session() -> Session:
    return SessionLocal()


def register_endpoint(name: str, url: str, method: str = "GET", expected_status: int = 200, interval_seconds: int = 60) -> Endpoint:
    """Register or update an endpoint to monitor."""
    with get_db_session() as session:
        ep = session.query(Endpoint).filter(Endpoint.url == url).first()
        if not ep:
            ep = Endpoint(
                name=name,
                url=url,
                method=method.upper(),
                expected_status=expected_status,
                interval_seconds=interval_seconds,
                is_active=True
            )
            session.add(ep)
        else:
            ep.name = name
            ep.method = method.upper()
            ep.expected_status = expected_status
            ep.interval_seconds = interval_seconds
            ep.is_active = True
        session.commit()
        session.refresh(ep)
        return ep


def record_check_result(
    endpoint_id: int,
    status_code: Optional[int],
    response_time_ms: float,
    is_success: bool,
    dns_time_ms: Optional[float] = None,
    ttfb_ms: Optional[float] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    content_length: Optional[int] = None
) -> MetricCheck:
    """Store an API probe result."""
    with get_db_session() as session:
        check = MetricCheck(
            endpoint_id=endpoint_id,
            status_code=status_code,
            response_time_ms=response_time_ms,
            dns_time_ms=dns_time_ms,
            ttfb_ms=ttfb_ms,
            is_success=is_success,
            error_type=error_type,
            error_message=error_message,
            content_length=content_length,
            checked_at=datetime.now(timezone.utc)
        )
        session.add(check)
        session.commit()
        session.refresh(check)
        return check
