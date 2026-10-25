from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import config
from monitor.database import Endpoint, MetricCheck, get_db_session


def calculate_percentiles(values: List[float], percentiles: List[int]) -> Dict[str, float]:
    """Calculate percentiles from a list of numerical values."""
    if not values:
        return {f"p{p}": 0.0 for p in percentiles}
    sorted_v = sorted(values)
    k = len(sorted_v)
    res = {}
    for p in percentiles:
        idx = int((p / 100.0) * k)
        idx = min(idx, k - 1)
        res[f"p{p}"] = round(sorted_v[idx], 2)
    return res


def get_endpoint_analytics(endpoint_id: int, hours: int = 24) -> Dict[str, Any]:
    """Compute detailed SLA, latency distribution, and error stats for an endpoint."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with get_db_session() as session:
        endpoint = session.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
        if not endpoint:
            return {}

        checks = (
            session.query(MetricCheck)
            .filter(MetricCheck.endpoint_id == endpoint_id, MetricCheck.checked_at >= cutoff)
            .order_by(MetricCheck.checked_at.desc())
            .all()
        )

        total_checks = len(checks)
        if total_checks == 0:
            return {
                "endpoint_id": endpoint.id,
                "name": endpoint.name,
                "url": endpoint.url,
                "total_checks": 0,
                "uptime_percentage": 100.0,
                "avg_response_ms": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "latest_status": "UNKNOWN",
                "latest_response_ms": None,
                "error_count": 0,
            }

        latencies = [c.response_time_ms for c in checks]
        successful = sum(1 for c in checks if c.is_success)
        failed = total_checks - successful
        uptime_pct = round((successful / total_checks) * 100.0, 2)

        percentiles = calculate_percentiles(latencies, [50, 90, 95, 99])
        avg_latency = round(sum(latencies) / total_checks, 2)
        latest = checks[0]

        # Status code counts
        status_codes: Dict[int, int] = {}
        for c in checks:
            sc = c.status_code or 0
            status_codes[sc] = status_codes.get(sc, 0) + 1

        return {
            "endpoint_id": endpoint.id,
            "name": endpoint.name,
            "url": endpoint.url,
            "total_checks": total_checks,
            "successful_checks": successful,
            "failed_checks": failed,
            "uptime_percentage": uptime_pct,
            "avg_response_ms": avg_latency,
            "min_response_ms": round(min(latencies), 2),
            "max_response_ms": round(max(latencies), 2),
            **percentiles,
            "status_codes": status_codes,
            "latest_status": "UP" if latest.is_success else "DOWN",
            "latest_status_code": latest.status_code,
            "latest_response_ms": round(latest.response_time_ms, 2),
            "last_checked": latest.checked_at.isoformat() if latest.checked_at else None,
        }


def generate_performance_insights() -> List[Dict[str, Any]]:
    """
    Analyzes historical metrics across all endpoints and produces actionable insights and warnings.
    """
    insights: List[Dict[str, Any]] = []

    with get_db_session() as session:
        endpoints = session.query(Endpoint).filter(Endpoint.is_active == True).all()
        for ep in endpoints:
            stats = get_endpoint_analytics(ep.id, hours=24)
            if stats.get("total_checks", 0) == 0:
                continue

            name = ep.name
            p95 = stats.get("p95", 0.0)
            avg = stats.get("avg_response_ms", 0.0)
            max_lat = stats.get("max_response_ms", 0.0)
            uptime = stats.get("uptime_percentage", 100.0)
            failed = stats.get("failed_checks", 0)

            # 1. Critical Downtime / Low SLA
            if uptime < 95.0:
                insights.append({
                    "severity": "CRITICAL",
                    "category": "AVAILABILITY",
                    "title": f"Degraded Availability on '{name}'",
                    "description": f"SLA uptime dropped to {uptime}% ({failed} failures in the last 24h). Target is >= 99.0%.",
                    "recommendation": "Investigate server logs, connection limits, and DNS resolution to prevent service outages.",
                    "endpoint_url": ep.url
                })
            elif uptime < 99.0:
                insights.append({
                    "severity": "WARNING",
                    "category": "AVAILABILITY",
                    "title": f"Sub-optimal Uptime on '{name}'",
                    "description": f"Availability is {uptime}%, showing occasional transient errors.",
                    "recommendation": "Implement exponential backoff retries and verify load balancer health-check intervals.",
                    "endpoint_url": ep.url
                })

            # 2. Slow Latency (p95 > SLOW_THRESHOLD)
            if p95 > config.CRITICAL_RESPONSE_THRESHOLD_MS:
                insights.append({
                    "severity": "CRITICAL",
                    "category": "LATENCY",
                    "title": f"Severe Latency Degradation on '{name}'",
                    "description": f"95% of requests take up to {p95}ms, surpassing the critical threshold of {config.CRITICAL_RESPONSE_THRESHOLD_MS}ms.",
                    "recommendation": "Inspect heavy database queries, add Redis caching, or scale application worker pods.",
                    "endpoint_url": ep.url
                })
            elif p95 > config.SLOW_RESPONSE_THRESHOLD_MS:
                insights.append({
                    "severity": "WARNING",
                    "category": "LATENCY",
                    "title": f"Elevated p95 Latency on '{name}'",
                    "description": f"p95 latency is {p95}ms (avg {avg}ms). Users on slow connections may experience noticeable delay.",
                    "recommendation": "Enable gzip/brotli compression and evaluate payload response payloads.",
                    "endpoint_url": ep.url
                })

            # 3. High Latency Jitter
            if max_lat > (avg * 4.0) and max_lat > 800:
                insights.append({
                    "severity": "INFO",
                    "category": "STABILITY",
                    "title": f"Latency Spikes Detected on '{name}'",
                    "description": f"Peak latency reached {max_lat}ms, which is >4x the average ({avg}ms).",
                    "recommendation": "Check for sporadic database connection pool exhaustion or cold start penalty.",
                    "endpoint_url": ep.url
                })

            # 4. Healthy confirmation
            if uptime >= 99.5 and p95 <= config.SLOW_RESPONSE_THRESHOLD_MS:
                insights.append({
                    "severity": "HEALTHY",
                    "category": "PERFORMANCE",
                    "title": f"Optimal Performance on '{name}'",
                    "description": f"Stable {uptime}% uptime with swift {p95}ms p95 latency.",
                    "recommendation": "Current performance adheres strictly to production SLA standards.",
                    "endpoint_url": ep.url
                })

    return insights
