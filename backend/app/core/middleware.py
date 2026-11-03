"""Production security, structured request logging, and rate limiting middlewares."""

import time
import uuid
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging

from app.core.config import settings
from app.core.logging import (
    request_id_ctx,
    client_ip_ctx,
    log_security_event,
)

req_logger = logging.getLogger("propval.access")


def get_client_ip(request: Request) -> str:
    """Resolve trusted client IP taking reverse proxy headers into account."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Correlation ID propagation and structured request access logging."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:12]}"
        client_ip = get_client_ip(request)

        # Bind context variables for structured logs
        token_req = request_id_ctx.set(req_id)
        token_ip = client_ip_ctx.set(client_ip)

        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = req_id
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            path = request.url.path

            # Log request outcome (health checks logged at DEBUG to reduce clutter)
            log_level = logging.DEBUG if path in ("/health", "/health/live", "/health/ready", "/api/v1/health") else logging.INFO
            req_logger.log(
                log_level,
                f"HTTP {request.method} {path} {status_code} ({duration_ms}ms)",
                extra={
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "request_id": req_id,
                    "client_ip": client_ip,
                },
            )

            # Reset context
            request_id_ctx.reset(token_req)
            client_ip_ctx.reset(token_ip)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce defense-in-depth HTTP security headers and secure cookie hygiene on all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # OWASP Recommended Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "font-src 'self' data:; "
            "connect-src 'self' http: https: ws:; "
            "frame-ancestors 'none';"
        )

        # Secure cookie flags hardening if Set-Cookie headers are returned
        if "set-cookie" in response.headers:
            cookie_headers = response.headers.getlist("set-cookie")
            response.headers.pop("set-cookie", None)
            for cookie in cookie_headers:
                if "Secure" not in cookie and settings.ENVIRONMENT == "production":
                    cookie += "; Secure"
                if "HttpOnly" not in cookie:
                    cookie += "; HttpOnly"
                if "SameSite" not in cookie:
                    cookie += "; SameSite=Strict"
                response.headers.append("set-cookie", cookie)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window IP rate limiter preventing brute-force and DoS exhaustion.

    Supports reverse-proxy real IP resolution (X-Forwarded-For, X-Real-IP) and
    actively prunes inactive IP keys to prevent memory exhaustion.
    """

    def __init__(self, app):
        super().__init__(app)
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.auth_request_history: Dict[str, List[float]] = defaultdict(list)

    def _cleanup_old_requests(self, history: List[float], window_seconds: float = 60.0) -> List[float]:
        cutoff = time.time() - window_seconds
        return [ts for ts in history if ts > cutoff]

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path

        # Health checks bypass rate limiting
        if path.startswith("/health") or path.startswith("/api/v1/health") or path == "/nginx-health":
            return await call_next(request)

        client_ip = get_client_ip(request)
        now = time.time()

        # Strict rate limit for authentication endpoints (prevent brute-force)
        if "/auth/" in path:
            ip_auth = self._cleanup_old_requests(self.auth_request_history[client_ip])
            if len(ip_auth) >= settings.RATE_LIMIT_AUTH_PER_MINUTE:
                log_security_event(
                    "RATE_LIMIT_EXCEEDED",
                    client_ip,
                    f"Authentication rate limit exceeded ({len(ip_auth)} req/min) on {path}",
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Authentication rate limit exceeded. Too many requests.",
                        "retry_after_seconds": 60,
                    },
                    headers={"Retry-After": "60"},
                )
            ip_auth.append(now)
            self.auth_request_history[client_ip] = ip_auth

        # Global rate limit
        ip_global = self._cleanup_old_requests(self.request_history[client_ip])
        if len(ip_global) >= settings.RATE_LIMIT_GLOBAL_PER_MINUTE:
            log_security_event(
                "RATE_LIMIT_EXCEEDED",
                client_ip,
                f"Global API rate limit exceeded ({len(ip_global)} req/min) on {path}",
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Global API rate limit exceeded. Please slow down.",
                    "retry_after_seconds": 60,
                },
                headers={"Retry-After": "60"},
            )
        ip_global.append(now)
        self.request_history[client_ip] = ip_global

        # Periodic dictionary key pruning to prevent memory growth
        if len(self.request_history) > 1000:
            for ip in list(self.request_history.keys()):
                cleaned = [t for t in self.request_history[ip] if t > now - 60.0]
                if not cleaned:
                    del self.request_history[ip]
                else:
                    self.request_history[ip] = cleaned

        return await call_next(request)
