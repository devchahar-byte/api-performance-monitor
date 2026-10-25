import argparse
import sys
import time
import schedule
from monitor.database import init_db, get_db_session, Endpoint, register_endpoint
from monitor.prober import probe_all_active_endpoints, probe_endpoint
from monitor.analytics import get_endpoint_analytics, generate_performance_insights
from monitor.exporter import export_performance_data


def cmd_init_db(args):
    init_db()
    print("Database initialized successfully with default monitoring endpoints.")


def cmd_probe(args):
    init_db()
    print("Executing probe across all active API endpoints...\n")
    results = probe_all_active_endpoints()
    export_performance_data()

    print(f"{'Status':<8}{'Code':<6}{'Latency':<12}{'TTFB':<10}{'Endpoint'}")
    print("-" * 75)
    for r in results:
        status_txt = "UP" if r["is_success"] else "DOWN"
        code_str = str(r["status_code"] or "ERR")
        lat_str = f"{r['response_time_ms']} ms"
        ttfb_str = f"{r['ttfb_ms']} ms" if r["ttfb_ms"] else "-"
        name_url = f"{r['endpoint_name']} ({r['url'][:30]})"
        print(f"{status_txt:<8}{code_str:<6}{lat_str:<12}{ttfb_str:<10}{name_url}")


def cmd_schedule(args):
    init_db()
    interval = args.interval
    print(f"=== API Performance Monitor Scheduler Started ===")
    print(f"Probe Interval: Every {interval} seconds")
    print(f"Press Ctrl+C to stop.\n")

    def job():
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Probing API endpoints...")
        results = probe_all_active_endpoints()
        export_performance_data()
        up_count = sum(1 for r in results if r["is_success"])
        print(f"  -> Completed probe: {up_count}/{len(results)} endpoints operational.\n")

    # Run immediately once
    job()

    schedule.every(interval).seconds.do(job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nScheduler stopped by user.")


def cmd_add(args):
    init_db()
    ep = register_endpoint(
        name=args.name,
        url=args.url,
        method=args.method,
        expected_status=args.expected_status,
        interval_seconds=args.interval
    )
    print(f"Endpoint registered: {ep.name} [{ep.method} {ep.url}]")
    print("Testing endpoint with initial probe...")
    res = probe_endpoint(ep)
    export_performance_data()
    status_str = "SUCCESS" if res["is_success"] else "FAILED"
    print(f"Probe Result: {status_str} (Status: {res['status_code']}, Latency: {res['response_time_ms']}ms)")


def cmd_endpoints(args):
    init_db()
    with get_db_session() as session:
        endpoints = session.query(Endpoint).all()
        if not endpoints:
            print("No endpoints registered.")
            return

        print(f"{'ID':<4}{'Status':<8}{'Uptime':<10}{'Avg Latency':<14}{'p95 Latency':<14}{'Endpoint Name'}")
        print("-" * 80)
        for ep in endpoints:
            stats = get_endpoint_analytics(ep.id, hours=24)
            status = stats.get("latest_status", "UNKNOWN")
            uptime = f"{stats.get('uptime_percentage', 100)}%"
            avg_lat = f"{stats.get('avg_response_ms', 0)} ms"
            p95_lat = f"{stats.get('p95', 0)} ms"
            print(f"{ep.id:<4}{status:<8}{uptime:<10}{avg_lat:<14}{p95_lat:<14}{ep.name}")


def cmd_insights(args):
    init_db()
    insights = generate_performance_insights()
    if not insights:
        print("No insights generated yet. Run 'python cli.py probe' to collect metrics first.")
        return

    print("=== Automated API Performance Insights & Recommendations ===\n")
    for idx, ins in enumerate(insights, 1):
        sev = ins["severity"]
        cat = ins["category"]
        print(f"[{idx}] [{sev}] {ins['title']} ({cat})")
        print(f"    Target:         {ins.get('endpoint_url')}")
        print(f"    Observation:    {ins['description']}")
        print(f"    Recommendation: {ins['recommendation']}\n")


def cmd_export(args):
    res = export_performance_data(output_json=args.json, output_csv=args.csv)
    print("Performance data exported successfully:")
    print(f"  JSON: {res['json']}")
    print(f"  CSV:  {res['csv']}")


def cmd_server(args):
    from app import app
    port = args.port
    print(f"=== Starting API Performance Monitor Server ===")
    print(f"Dashboard URL: http://localhost:{port}")
    print(f"Prometheus Metrics URL: http://localhost:{port}/metrics")
    print("Press Ctrl+C to stop.\n")
    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    parser = argparse.ArgumentParser(description="API Performance Monitor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    subparsers.add_parser("init-db", help="Initialize the SQLite database schema")

    subparsers.add_parser("probe", help="Execute an immediate probe cycle across all endpoints")

    p_sched = subparsers.add_parser("schedule", help="Start continuous periodic monitoring loop")
    p_sched.add_argument("--interval", type=int, default=60, help="Check interval in seconds (default: 60)")

    p_add = subparsers.add_parser("add", help="Register a new API endpoint to monitor")
    p_add.add_argument("name", help="Human-readable name for the endpoint")
    p_add.add_argument("url", help="API URL to probe")
    p_add.add_argument("--method", default="GET", choices=["GET", "POST", "HEAD"], help="HTTP method")
    p_add.add_argument("--expected-status", type=int, default=200, help="Expected HTTP status code")
    p_add.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds")

    subparsers.add_parser("endpoints", help="List monitored endpoints and performance statistics")

    subparsers.add_parser("insights", help="Display performance insights and SLA recommendations")

    p_exp = subparsers.add_parser("export", help="Export performance metrics to JSON and CSV")
    p_exp.add_argument("--json", default=None, help="Custom output path for JSON export")
    p_exp.add_argument("--csv", default=None, help="Custom output path for CSV export")

    p_srv = subparsers.add_parser("server", help="Start Flask API and live dashboard server")
    p_srv.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")

    args = parser.parse_args()

    commands = {
        "init-db": cmd_init_db,
        "probe": cmd_probe,
        "schedule": cmd_schedule,
        "add": cmd_add,
        "endpoints": cmd_endpoints,
        "insights": cmd_insights,
        "export": cmd_export,
        "server": cmd_server,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
