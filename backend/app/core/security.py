import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline HTTP security headers to all API responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class SlidingWindowRateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter (60s window) for API protection."""

    def __init__(self, app, max_requests_per_minute: int = 120) -> None:
        super().__init__(app)
        self.max_requests = max(0, max_requests_per_minute)
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.max_requests <= 0 or request.url.path.endswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - 60.0

        with self._lock:
            bucket = self._hits[client_ip]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please wait before retrying."},
                    headers={"Retry-After": "60", "X-RateLimit-Limit": str(self.max_requests)},
                )
            bucket.append(now)
            remaining = max(0, self.max_requests - len(bucket))

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
