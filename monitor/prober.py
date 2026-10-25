import logging
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
import config
from monitor.database import Endpoint, get_db_session, record_check_result

logger = logging.getLogger(__name__)


def probe_endpoint(endpoint: Endpoint) -> Dict[str, Any]:
    """
    Executes an HTTP request to an API endpoint and measures latency and status metrics.
    """
    url = endpoint.url
    method = endpoint.method.upper()
    expected_status = endpoint.expected_status
    timeout = config.DEFAULT_REQUEST_TIMEOUT

    start_time = time.perf_counter()
    status_code: Optional[int] = None
    dns_time_ms: Optional[float] = None
    ttfb_ms: Optional[float] = None
    content_length: Optional[int] = None
    is_success = False
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    try:
        # Measure initial request
        session = requests.Session()
        req_start = time.perf_counter()
        
        response = session.request(
            method=method,
            url=url,
            timeout=timeout,
            headers={"User-Agent": "APIPerformanceMonitor/1.0", "Accept": "*/*"},
            stream=True
        )
        
        ttfb = (time.perf_counter() - req_start) * 1000.0
        ttfb_ms = ttfb

        # Read content to measure total elapsed time and content length
        content = response.content
        total_time_ms = (time.perf_counter() - start_time) * 1000.0

        status_code = response.status_code
        content_length = len(content)
        
        if status_code == expected_status or (200 <= status_code < 400 and expected_status == 200):
            is_success = True
        else:
            is_success = False
            error_type = "HTTP_STATUS_MISMATCH"
            error_message = f"Expected status {expected_status}, received {status_code}"

    except Timeout as e:
        total_time_ms = (time.perf_counter() - start_time) * 1000.0
        is_success = False
        error_type = "TIMEOUT"
        error_message = f"Request timed out after {timeout}s: {e}"
    except ConnectionError as e:
        total_time_ms = (time.perf_counter() - start_time) * 1000.0
        is_success = False
        error_type = "CONNECTION_ERROR"
        error_message = f"Failed to connect to host: {e}"
    except RequestException as e:
        total_time_ms = (time.perf_counter() - start_time) * 1000.0
        is_success = False
        error_type = "REQUEST_EXCEPTION"
        error_message = str(e)
    except Exception as e:
        total_time_ms = (time.perf_counter() - start_time) * 1000.0
        is_success = False
        error_type = "INTERNAL_ERROR"
        error_message = str(e)

    # Persist probe result to SQLite
    record_check_result(
        endpoint_id=endpoint.id,
        status_code=status_code,
        response_time_ms=total_time_ms,
        dns_time_ms=dns_time_ms,
        ttfb_ms=ttfb_ms,
        is_success=is_success,
        error_type=error_type,
        error_message=error_message,
        content_length=content_length
    )

    return {
        "endpoint_id": endpoint.id,
        "endpoint_name": endpoint.name,
        "url": url,
        "status_code": status_code,
        "response_time_ms": round(total_time_ms, 2),
        "ttfb_ms": round(ttfb_ms, 2) if ttfb_ms else None,
        "is_success": is_success,
        "error_type": error_type,
        "error_message": error_message,
    }


def probe_all_active_endpoints() -> List[Dict[str, Any]]:
    """Probe all active endpoints in the database."""
    results = []
    with get_db_session() as session:
        endpoints = session.query(Endpoint).filter(Endpoint.is_active == True).all()
        for ep in endpoints:
            logger.info(f"Probing API endpoint: {ep.name} ({ep.url})")
            res = probe_endpoint(ep)
            results.append(res)
    return results
