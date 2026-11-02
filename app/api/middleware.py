import json
import logging
import time
import uuid
from collections import defaultdict, deque
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

request_id_var = ContextVar("request_id", default="")
logger = logging.getLogger("rof12.api")
SENSITIVE = {"authorization", "cookie", "x-api-key", "password", "token", "secret"}


def sanitized_log(data: dict) -> dict:
    return {key: "[REDACTED]" if key.lower() in SENSITIVE else value for key, value in data.items()}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = rid
        token = request_id_var.set(rid)
        started = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            context = getattr(request.state, "auth_context", None)
            logger.info(json.dumps(sanitized_log({"event": "http_request", "request_id": rid, "tenant_id": getattr(context, "tenant_id", None), "method": request.method, "path": request.url.path, "latency_ms": int((time.monotonic() - started) * 1000)}), sort_keys=True))
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit=30, window_seconds=60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self.hits = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} or request.url.path.startswith("/v1/security/"):
            key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
            now = time.monotonic()
            hits = self.hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                rid = getattr(request.state, "request_id", str(uuid.uuid4()))
                return JSONResponse({"code": "RATE_LIMITED", "message": "rate limit exceeded", "request_id": rid}, status_code=429, headers={"X-Request-ID": rid})
            hits.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply browser hardening consistently, including static UI responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

