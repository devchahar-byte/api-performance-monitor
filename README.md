# ⚡ API Performance Monitor

A high-performance, production-ready system to track, analyze, and optimize API performance metrics, response latencies, and error rates. Built with **Python (Flask, Requests)**, **Grafana**, and **SQLite**, with automated **GitHub Pages** live web dashboard publishing.

---

## 🚀 Key Features

- **High-Precision Latency Tracking**: Accurately measures total response time, Time to First Byte (TTFB), DNS resolution, and HTTP status codes using Python `requests`.
- **Statistical Percentiles & SLA Uptime**: Automatically calculates **p50**, **p90**, **p95**, and **p99** tail latencies along with 24-hour rolling SLA availability percentages.
- **Rule-Based Insights & Recommendations**: Generates automated engineering recommendations for detected bottlenecks (e.g. slow p95 tail latencies, degraded availability, or latency jitter spikes).
- **Interactive Live Web Dashboard (GitHub Pages Ready)**: Modern, responsive dashboard in `docs/index.html` with real-time KPI metrics, Chart.js response time graphs, SLA health badges, and instant CSV/JSON exports.
- **Automated Git-Monitoring CI/CD**: Integrated `.github/workflows/monitor_and_publish.yml` that runs periodically (every 30 minutes), probes all registered endpoints, stores results, and updates the live GitHub Pages dashboard automatically.
- **Prometheus & Grafana Ready**: Native `/metrics` Prometheus exporter and pre-configured Grafana dashboards (`grafana/dashboards/api_performance.json`) and datasources (`docker-compose.yml`).
- **RESTful Management API**: Endpoints to list metrics, register new API endpoints, trigger manual probe cycles, and fetch health insights.

---

## 🏗️ Architecture

```
                                +-----------------------------+
                                |  GitHub Actions / Scheduler |
                                +-----------------------------+
                                               |
                                               v
                          +-----------------------------------------+
                          | Python Prober Engine (Requests)         |
                          |  - Total Latency (ms)                   |
                          |  - Time to First Byte (TTFB)            |
                          |  - Status Code Verification             |
                          +-----------------------------------------+
                                               |
                                               v
                          +-----------------------------------------+
                          | SQLite Database (SQLAlchemy)            |
                          |  - endpoints (registered APIs)          |
                          |  - metric_checks (probe audit log)      |
                          +-----------------------------------------+
                                               |
                                               v
    +------------------------------------------+------------------------------------------+
    |                                          |                                          |
    v                                          v                                          v
+--------------------------+       +--------------------------+       +--------------------------+
| Analytics Engine         |       | Prometheus Exporter      |       | Live Web Dashboard       |
|  - p50, p90, p95, p99    |       |  -> GET /metrics         |       |  - docs/index.html       |
|  - SLA Uptime %          |       |  -> Grafana Dashboards   |       |  - GitHub Pages deploy   |
|  - Automated Insights    |       |  -> Docker Compose       |       |  - CSV / JSON export     |
+--------------------------+       +--------------------------+       +--------------------------+
```

---

## 📂 Project Structure

```
api-performance-monitor/
├── .github/workflows/
│   └── monitor_and_publish.yml  # Automated CI/CD scheduled probe & Pages deploy
├── docs/                        # Live Web Dashboard (GitHub Pages root)
│   ├── index.html               # Interactive web app (Tailwind CSS, Chart.js)
│   ├── data.json                # Live performance stream
│   └── metrics.csv              # Downloadable metrics dataset
├── monitor/
│   ├── __init__.py
│   ├── database.py              # SQLite models (Endpoint, MetricCheck) & sessions
│   ├── prober.py                # HTTP prober measuring latency and TTFB
│   ├── analytics.py             # Percentiles (p50/p95/p99) & automated insights
│   └── exporter.py              # Exports metrics to JSON/CSV
├── grafana/
│   ├── dashboards/              # Pre-configured Grafana dashboard JSON
│   └── datasources/             # Prometheus datasource provisioning
├── tests/                       # Pytest test suite (database, analytics, API)
├── app.py                       # Flask REST API & Prometheus /metrics exporter
├── cli.py                       # Command line interface
├── config.py                    # Application configuration
├── docker-compose.yml           # Multi-container setup (Flask + Prometheus + Grafana)
├── Dockerfile                   # Application container definition
├── requirements.txt             # Python dependencies
└── pytest.ini                   # Pytest configuration
```

---

## 🛠️ Quickstart Installation

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/devchahar-byte/api-performance-monitor.git
cd api-performance-monitor

# Create virtual environment
python -m venv .venv

# Activate:
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
```

### 2. Initialize Database & Run Initial Probes

```bash
python cli.py init-db
python cli.py probe
python cli.py insights
```

---

## 💻 CLI Usage

The `cli.py` tool provides quick management capabilities:

```bash
# 1. Run an immediate probe across all active endpoints
python cli.py probe

# 2. View performance statistics & SLA uptime
python cli.py endpoints

# 3. View automated engineering insights & recommendations
python cli.py insights

# 4. Register a new API endpoint to monitor
python cli.py add "Production Auth API" "https://api.example.com/auth/health" --method GET --expected-status 200

# 5. Start the local scheduler loop (e.g. check every 30 seconds)
python cli.py schedule --interval 30

# 6. Export metrics to JSON & CSV
python cli.py export

# 7. Start the Flask Web Dashboard & Prometheus API
python cli.py server --port 5000
```

---

## 🌐 Live Web Page & GitHub Pages

This project is pre-configured for automated **GitHub Pages** hosting:
- Live Dashboard: `https://devchahar-byte.github.io/api-performance-monitor/`
- Every 30 minutes, GitHub Actions automatically executes the prober, records latencies into SQLite, computes percentiles, updates `docs/data.json`, and refreshes the live webpage.
- To preview locally:
  ```bash
  python cli.py server --port 5000
  ```
  Open `http://localhost:5000` in your browser.

---

## 📊 Grafana & Prometheus Integration

To run the complete observability stack (Monitor App + Prometheus + Grafana):

```bash
docker-compose up --build -d
```

- **Flask Monitor API**: `http://localhost:5000`
- **Prometheus Metrics**: `http://localhost:5000/metrics`
- **Prometheus Server**: `http://localhost:9090`
- **Grafana Dashboard**: `http://localhost:3000` (User: `admin`, Password: `admin`)

The Grafana dashboard comes pre-provisioned with panels for:
- Overall SLA Uptime (%) Gauge
- Total Operational Endpoints
- Current Latencies (ms) Bar chart
- Response Time Latency Timeseries graph

---

## 🧪 Running Unit Tests

Run the test suite with `pytest`:

```bash
pytest -v
```

All 7 test suites verify:
- Database schema and metric persistence
- Percentile calculations (p50, p90, p95, p99)
- Automated insight and warning generation
- Flask REST routes & Prometheus metrics formatting

---

## 📄 License
MIT License. Created for automated API performance analysis.
