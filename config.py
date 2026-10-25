import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DATABASE_PATH = os.getenv("MONITOR_DB_PATH", str(DATA_DIR / "monitor.db"))
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Monitoring Thresholds & Settings
DEFAULT_CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
DEFAULT_REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10.0"))
SLOW_RESPONSE_THRESHOLD_MS = float(os.getenv("SLOW_THRESHOLD_MS", "500.0"))
CRITICAL_RESPONSE_THRESHOLD_MS = float(os.getenv("CRITICAL_THRESHOLD_MS", "1500.0"))

# Default monitored endpoints for demonstration & initial probing
DEFAULT_ENDPOINTS = [
    {
        "name": "JSONPlaceholder Posts API",
        "url": "https://jsonplaceholder.typicode.com/posts/1",
        "method": "GET",
        "expected_status": 200,
        "interval_seconds": 60,
    },
    {
        "name": "JSONPlaceholder Users API",
        "url": "https://jsonplaceholder.typicode.com/users",
        "method": "GET",
        "expected_status": 200,
        "interval_seconds": 60,
    },
    {
        "name": "HTTPBin Status 200 Check",
        "url": "https://httpbin.org/status/200",
        "method": "GET",
        "expected_status": 200,
        "interval_seconds": 60,
    },
    {
        "name": "HTTPBin Delay Simulation (Slow)",
        "url": "https://httpbin.org/delay/1",
        "method": "GET",
        "expected_status": 200,
        "interval_seconds": 120,
    }
]
