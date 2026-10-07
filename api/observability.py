from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import Counter

from fastapi import Request
from starlette.responses import Response

logger = logging.getLogger("form8825.api")


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests = Counter()
        self.statuses = Counter()
        self.total_duration_seconds = 0.0

    def observe(self, method: str, path: str, status: int, duration: float) -> None:
        with self._lock:
            self.requests[(method, path)] += 1
            self.statuses[status] += 1
            self.total_duration_seconds += duration

    def render_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP form8825_http_requests_total HTTP requests by method and path.",
                "# TYPE form8825_http_requests_total counter",
            ]
            for (method, path), value in sorted(self.requests.items()):
                lines.append(
                    f'form8825_http_requests_total{{method="{method}",path="{path}"}} {value}'
                )
            lines += [
                "# HELP form8825_http_responses_total HTTP responses by status.",
                "# TYPE form8825_http_responses_total counter",
            ]
            for status, value in sorted(self.statuses.items()):
                lines.append(f'form8825_http_responses_total{{status="{status}"}} {value}')
            lines += [
                "# HELP form8825_http_request_duration_seconds_total Cumulative request duration.",
                "# TYPE form8825_http_request_duration_seconds_total counter",
                f"form8825_http_request_duration_seconds_total {self.total_duration_seconds:.6f}",
            ]
            return "\n".join(lines) + "\n"


metrics = Metrics()


async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        metrics.observe(request.method, request.url.path, status, duration)
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": round(duration * 1000, 3),
                },
                sort_keys=True,
            )
        )
        # Response may not exist if call_next raised.
        if "response" in locals():
            response.headers["X-Request-ID"] = request_id


def metrics_response() -> Response:
    return Response(metrics.render_prometheus(), media_type="text/plain; version=0.0.4")
