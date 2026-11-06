"""Circuit Breaker resilience pattern for PropVal AI external provider integrations.

Protects against cascading failures and API flooding by stopping outbound requests
to degrading or offline data provider gateways.
"""

from datetime import datetime, timezone
from enum import Enum
import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("propval.connectors.circuit_breaker")


class CircuitBreakerState(str, Enum):
    """Operational states of the circuit breaker."""
    CLOSED = "CLOSED"        # Normal operation: requests flow freely
    OPEN = "OPEN"            # Tripped: requests are short-circuited immediately
    HALF_OPEN = "HALF_OPEN"  # Recovery testing: limited trial requests allowed


class CircuitBreaker:
    """Thread-safe circuit breaker protecting external provider HTTP endpoints."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        half_open_success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout_seconds = max(0.01, recovery_timeout_seconds)
        self.half_open_success_threshold = max(1, half_open_success_threshold)

        self._lock = threading.Lock()
        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.monotonic()
        self._total_requests = 0
        self._total_failures = 0
        self._total_short_circuits = 0

    @property
    def state(self) -> CircuitBreakerState:
        with self._lock:
            self._evaluate_state()
            return self._state

    def _evaluate_state(self) -> None:
        """Internal state transition check based on recovery timeout."""
        if self._state == CircuitBreakerState.OPEN:
            elapsed = time.monotonic() - (self._last_failure_time or self._last_state_change)
            if elapsed >= self.recovery_timeout_seconds:
                self._state = CircuitBreakerState.HALF_OPEN
                self._consecutive_successes = 0
                self._last_state_change = time.monotonic()
                logger.info(
                    f"CircuitBreaker[{self.name}] Transitioned from OPEN to HALF_OPEN after {elapsed:.1f}s cooldown."
                )

    def can_execute(self) -> bool:
        """Check if a request is permitted to proceed."""
        with self._lock:
            self._evaluate_state()
            self._total_requests += 1

            if self._state == CircuitBreakerState.OPEN:
                self._total_short_circuits += 1
                return False

            if self._state == CircuitBreakerState.HALF_OPEN:
                # In HALF_OPEN, allow limited probe traffic
                return True

            # In CLOSED, all requests permitted
            return True

    def record_success(self) -> None:
        """Record a successful provider interaction."""
        with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._consecutive_successes += 1
                if self._consecutive_successes >= self.half_open_success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._consecutive_failures = 0
                    self._consecutive_successes = 0
                    self._last_state_change = time.monotonic()
                    logger.info(
                        f"CircuitBreaker[{self.name}] Reset to CLOSED following "
                        f"{self.half_open_success_threshold} consecutive recovery successes."
                    )
            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure counter on successful execution
                self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Record an interaction failure (e.g., 5xx, timeout, connect failure)."""
        with self._lock:
            self._total_failures += 1
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Any failure in HALF_OPEN trips immediately back to OPEN
                self._state = CircuitBreakerState.OPEN
                self._last_state_change = time.monotonic()
                logger.warning(
                    f"CircuitBreaker[{self.name}] Probe failed in HALF_OPEN state. "
                    f"Tripping circuit back to OPEN."
                )
            elif self._state == CircuitBreakerState.CLOSED:
                if self._consecutive_failures >= self.failure_threshold:
                    self._state = CircuitBreakerState.OPEN
                    self._last_state_change = time.monotonic()
                    logger.warning(
                        f"CircuitBreaker[{self.name}] Failure threshold reached "
                        f"({self._consecutive_failures}/{self.failure_threshold}). Tripping circuit to OPEN."
                    )

    def get_remaining_cooldown_seconds(self) -> float:
        """Get remaining cooldown seconds if circuit is OPEN."""
        with self._lock:
            if self._state != CircuitBreakerState.OPEN:
                return 0.0
            elapsed = time.monotonic() - (self._last_failure_time or self._last_state_change)
            remaining = self.recovery_timeout_seconds - elapsed
            return max(0.0, remaining)

    def reset(self) -> None:
        """Manually force-reset the circuit breaker to CLOSED."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._last_state_change = time.monotonic()
            self._last_failure_time = None
            logger.info(f"CircuitBreaker[{self.name}] Manually reset to CLOSED state.")

    def trip(self) -> None:
        """Manually trip the circuit breaker to OPEN (e.g. for maintenance or emergency)."""
        with self._lock:
            self._state = CircuitBreakerState.OPEN
            self._consecutive_failures = self.failure_threshold
            self._last_failure_time = time.monotonic()
            self._last_state_change = time.monotonic()
            logger.warning(f"CircuitBreaker[{self.name}] Manually tripped to OPEN state.")

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic metrics for operational dashboards."""
        with self._lock:
            self._evaluate_state()
            return {
                "name": self.name,
                "state": self._state.value,
                "consecutive_failures": self._consecutive_failures,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout_seconds": self.recovery_timeout_seconds,
                "remaining_cooldown_seconds": round(self.get_remaining_cooldown_seconds(), 2),
                "total_requests": self._total_requests,
                "total_failures": self._total_failures,
                "total_short_circuits": self._total_short_circuits,
            }


class CircuitBreakerRegistry:
    """Global registry maintaining circuit breakers across all providers."""

    _breakers: Dict[str, CircuitBreaker] = {}
    _lock = threading.Lock()

    @classmethod
    def get_or_create(
        cls,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        half_open_success_threshold: int = 2,
    ) -> CircuitBreaker:
        key = name.lower()
        with cls._lock:
            if key not in cls._breakers:
                cls._breakers[key] = CircuitBreaker(
                    name=key,
                    failure_threshold=failure_threshold,
                    recovery_timeout_seconds=recovery_timeout_seconds,
                    half_open_success_threshold=half_open_success_threshold,
                )
            return cls._breakers[key]

    @classmethod
    def get_status_all(cls) -> Dict[str, Dict[str, Any]]:
        with cls._lock:
            return {k: b.get_status() for k, b in cls._breakers.items()}

    @classmethod
    def reset_all(cls) -> None:
        with cls._lock:
            for b in cls._breakers.values():
                b.reset()
