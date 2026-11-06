"""Exceptions for PropVal AI data connectors."""

from typing import Optional


class ConnectorError(Exception):
    """Base exception for all connector errors."""
    pass


class AuthenticationError(ConnectorError):
    """Raised when authentication with data source fails."""
    pass


class ExpiredCredentialError(AuthenticationError):
    """Raised when provider API credentials or licensing period has expired."""
    def __init__(self, message: str, provider: Optional[str] = None, expired_at: Optional[str] = None):
        super().__init__(message)
        self.provider = provider
        self.expired_at = expired_at


class RateLimitExceededError(ConnectorError):
    """Raised when connector exceeds source rate limit."""
    def __init__(self, message: str, retry_after_seconds: Optional[int] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class NetworkTimeoutError(ConnectorError):
    """Raised when source request times out."""
    pass


class InvalidResponseError(ConnectorError):
    """Raised when source returns malformed or unexpected payload."""
    pass


class SecurityViolationError(ConnectorError):
    """Raised when an SSRF attempt, DNS rebinding, or disallowed destination URL is detected."""
    pass


class PayloadTooLargeError(ConnectorError):
    """Raised when request or response body exceeds maximum allowed institutional size limit."""
    pass


class CircuitBreakerOpenError(ConnectorError):
    """Raised when outbound request is short-circuited due to OPEN circuit breaker."""
    def __init__(self, message: str, provider: str, reset_timeout_seconds: float):
        super().__init__(message)
        self.provider = provider
        self.reset_timeout_seconds = reset_timeout_seconds
