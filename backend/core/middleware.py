from collections import defaultdict, deque
from time import monotonic
from typing import Iterable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .metrics import metrics_registry


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'; object-src 'none'; frame-ancestors 'none'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        for name, value in headers.items():
            response.headers.setdefault(name, value)
        return response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        max_requests: int,
        window_seconds: int,
        protected_prefixes: Iterable[str] = ("/api",),
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.protected_prefixes = tuple(protected_prefixes)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or not request.url.path.startswith(self.protected_prefixes):
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.url.path}"
        now = monotonic()
        hits = self._hits[key]

        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Batas permintaan terlampaui. Silakan coba lagi nanti."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        hits.append(now)
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = monotonic()
        response = await call_next(request)
        metrics_registry.record(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_seconds=monotonic() - start,
        )
        return response
