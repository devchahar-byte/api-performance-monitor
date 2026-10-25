import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import config
from monitor.database import Endpoint, MetricCheck, get_db_session, init_db
from monitor.analytics import get_endpoint_analytics, generate_performance_insights


def export_performance_data(output_json: Optional[str] = None, output_csv: Optional[str] = None) -> Dict[str, str]:
    """
    Exports endpoints, recent checks, statistical analytics, and insights
    to JSON and CSV files for the live web dashboard.
    """
    init_db()

    with get_db_session() as session:
        endpoints = session.query(Endpoint).all()
        checks = (
            session.query(MetricCheck)
            .order_by(MetricCheck.checked_at.desc())
            .limit(100)
            .all()
        )

        endpoints_data = []
        for ep in endpoints:
            stats = get_endpoint_analytics(ep.id, hours=24)
            endpoints_data.append(stats)

        checks_data = [c.to_dict() for c in checks]

    insights = generate_performance_insights()

    # Aggregate top-level metrics
    total_probes = sum(ep.get("total_checks", 0) for ep in endpoints_data)
    total_successful = sum(ep.get("successful_checks", 0) for ep in endpoints_data)
    overall_uptime = round((total_successful / total_probes) * 100.0, 2) if total_probes > 0 else 100.0
    active_endpoints = len(endpoints_data)
    avg_latency = (
        round(sum(ep.get("avg_response_ms", 0.0) for ep in endpoints_data) / active_endpoints, 2)
        if active_endpoints > 0 else 0.0
    )

    payload: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_endpoints": active_endpoints,
            "overall_uptime_pct": overall_uptime,
            "overall_avg_latency_ms": avg_latency,
            "total_checks_recorded": total_probes,
        },
        "endpoints": endpoints_data,
        "recent_checks": checks_data,
        "insights": insights,
    }

    # 1. Write JSON
    json_path = Path(output_json) if output_json else (config.DOCS_DIR / "data.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # 2. Write CSV
    csv_path = Path(output_csv) if output_csv else (config.DOCS_DIR / "metrics.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "endpoint_id", "endpoint_name", "status_code",
        "response_time_ms", "ttfb_ms", "is_success", "error_type", "checked_at"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for c in checks_data:
            writer.writerow(c)

    return {
        "json": str(json_path.resolve()),
        "csv": str(csv_path.resolve())
    }
