import os
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, Response
import config
from monitor.database import init_db, get_db_session, Endpoint, MetricCheck, register_endpoint
from monitor.prober import probe_endpoint, probe_all_active_endpoints
from monitor.analytics import get_endpoint_analytics, generate_performance_insights
from monitor.exporter import export_performance_data

app = Flask(__name__, static_folder="docs", static_url_path="")
init_db()


@app.route("/")
def index():
    """Serve the interactive web monitoring dashboard."""
    return send_from_directory(config.DOCS_DIR, "index.html")


@app.route("/data.json")
def serve_data_json():
    return send_from_directory(config.DOCS_DIR, "data.json")


@app.route("/metrics.csv")
def serve_metrics_csv():
    return send_from_directory(config.DOCS_DIR, "metrics.csv")


@app.route("/api/endpoints", methods=["GET"])
def get_endpoints_api():
    """List all registered endpoints with 24-hour performance analytics."""
    with get_db_session() as session:
        endpoints = session.query(Endpoint).all()
        results = [get_endpoint_analytics(ep.id, hours=24) for ep in endpoints]
    return jsonify(results)


@app.route("/api/endpoints", methods=["POST"])
def add_endpoint_api():
    """Register a new endpoint to monitor."""
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    url = data.get("url")
    method = data.get("method", "GET")
    expected_status = int(data.get("expected_status", 200))
    interval = int(data.get("interval_seconds", 60))

    if not name or not url:
        return jsonify({"error": "Fields 'name' and 'url' are required"}), 400

    ep = register_endpoint(
        name=name,
        url=url,
        method=method,
        expected_status=expected_status,
        interval_seconds=interval
    )
    # Immediately probe the newly added endpoint
    probe_endpoint(ep)
    export_performance_data()
    return jsonify({"message": "Endpoint registered and initial probe executed", "endpoint": ep.to_dict()}), 201


@app.route("/api/probe", methods=["POST"])
def trigger_probe_api():
    """Trigger an on-demand probe cycle for all active endpoints."""
    results = probe_all_active_endpoints()
    export_performance_data()
    return jsonify({"message": f"Successfully probed {len(results)} endpoints", "results": results})


@app.route("/api/metrics", methods=["GET"])
def get_metrics_api():
    """Get recent time-series checks (with optional limit and endpoint_id filters)."""
    limit = int(request.args.get("limit", 50))
    endpoint_id = request.args.get("endpoint_id", type=int)

    with get_db_session() as session:
        query = session.query(MetricCheck).order_by(MetricCheck.checked_at.desc())
        if endpoint_id:
            query = query.filter(MetricCheck.endpoint_id == endpoint_id)
        checks = query.limit(limit).all()
        return jsonify([c.to_dict() for c in checks])


@app.route("/api/insights", methods=["GET"])
def get_insights_api():
    """Retrieve actionable performance insights and SLA alerts."""
    insights = generate_performance_insights()
    return jsonify(insights)


@app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """
    Exposes metrics in Prometheus format for Grafana ingestion.
    """
    lines = [
        "# HELP api_response_time_ms Latest API response latency in milliseconds",
        "# TYPE api_response_time_ms gauge",
        "# HELP api_uptime_status Current operational status (1 = UP, 0 = DOWN)",
        "# TYPE api_uptime_status gauge",
        "# HELP api_sla_uptime_percent SLA uptime percentage over the last 24 hours",
        "# TYPE api_sla_uptime_percent gauge",
    ]

    with get_db_session() as session:
        endpoints = session.query(Endpoint).filter(Endpoint.is_active == True).all()
        for ep in endpoints:
            stats = get_endpoint_analytics(ep.id, hours=24)
            safe_name = ep.name.replace('"', '\\"')
            safe_url = ep.url.replace('"', '\\"')
            latency = stats.get("latest_response_ms") or 0.0
            is_up = 1 if stats.get("latest_status") == "UP" else 0
            uptime = stats.get("uptime_percentage", 100.0)

            lines.append(f'api_response_time_ms{{endpoint="{safe_name}",url="{safe_url}"}} {latency}')
            lines.append(f'api_uptime_status{{endpoint="{safe_name}"}} {is_up}')
            lines.append(f'api_sla_uptime_percent{{endpoint="{safe_name}"}} {uptime}')

    return Response("\n".join(lines) + "\n", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting API Performance Monitor server at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
