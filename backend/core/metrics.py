from collections import defaultdict
from dataclasses import dataclass
from threading import Lock


@dataclass
class RouteMetric:
    count: int = 0
    latency_seconds_total: float = 0.0


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, str, int], RouteMetric] = defaultdict(RouteMetric)

    def record(self, *, method: str, path: str, status_code: int, latency_seconds: float) -> None:
        key = (method, path, status_code)
        with self._lock:
            metric = self._requests[key]
            metric.count += 1
            metric.latency_seconds_total += latency_seconds

    def render_prometheus(self) -> str:
        lines = [
            "# HELP heritageguard_http_requests_total Total HTTP requests.",
            "# TYPE heritageguard_http_requests_total counter",
        ]

        with self._lock:
            items = list(self._requests.items())

        for (method, path, status_code), metric in items:
            labels = f'method="{method}",path="{path}",status_code="{status_code}"'
            lines.append(f"heritageguard_http_requests_total{{{labels}}} {metric.count}")

        lines.extend(
            [
                "# HELP heritageguard_http_request_latency_seconds_total Total HTTP request latency in seconds.",
                "# TYPE heritageguard_http_request_latency_seconds_total counter",
            ]
        )
        for (method, path, status_code), metric in items:
            labels = f'method="{method}",path="{path}",status_code="{status_code}"'
            lines.append(
                f"heritageguard_http_request_latency_seconds_total{{{labels}}} "
                f"{metric.latency_seconds_total:.6f}"
            )

        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
