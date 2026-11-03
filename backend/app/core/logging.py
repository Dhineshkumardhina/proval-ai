"""Structured logging, security event tracking, and credential/PII redaction."""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable for request tracing across async tasks
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
client_ip_ctx: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)

# Patterns matching sensitive parameters and secrets
SENSITIVE_PATTERNS = [
    (re.compile(r'(password|secret|jwt|token|api_key|authorization|bearer)\s*[:=]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1: "[REDACTED]"'),
    (re.compile(r'Bearer\s+[A-Za-z0-9\-_\.=]+', re.IGNORECASE), 'Bearer [REDACTED]'),
    (re.compile(r'\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b'), '[REDACTED_AADHAAR]'),
    (re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'), '[REDACTED_PAN]'),
    (re.compile(r'(postgres(ql)?:\/\/[^:]+:)([^@]+)(@)', re.IGNORECASE), r'\1[REDACTED]\4'),
]


def redact_sensitive_text(text: str) -> str:
    """Scrub sensitive credentials, tokens, PII, and connection strings from text."""
    if not isinstance(text, str):
        return text
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class SensitiveDataRedactor(logging.Filter):
    """Logging filter that scrubs sensitive secrets and PII from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_sensitive_text(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(redact_sensitive_text(str(v)) if isinstance(v, str) else v for v in record.args)
        return True


class StructuredJsonFormatter(logging.Formatter):
    """JSON log formatter adhering to cloud-native structured observability standards."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Correlation tracing
        req_id = request_id_ctx.get() or getattr(record, "request_id", None)
        if req_id:
            log_payload["requestId"] = req_id

        ip = client_ip_ctx.get() or getattr(record, "client_ip", None)
        if ip:
            log_payload["clientIp"] = ip

        # Structured request attributes
        for attr in ("method", "path", "status_code", "duration_ms", "security_event"):
            if hasattr(record, attr):
                log_payload[attr] = getattr(record, attr)

        # Exception details
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)


def setup_logging(environment: str = "production", log_level: str = "INFO") -> None:
    """Initialize system-wide structured logging and redactor filter."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.addFilter(SensitiveDataRedactor())

    if environment == "production":
        stream_handler.setFormatter(StructuredJsonFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(stream_handler)

    # Lower noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


# Dedicated security auditor logger
security_logger = logging.getLogger("propval.security")


def log_security_event(
    event_type: str,
    client_ip: str,
    detail: str,
    user: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an immutable security audit event."""
    extra_dict: Dict[str, Any] = {
        "security_event": event_type,
        "client_ip": client_ip,
        "detail": detail,
    }
    if user:
        extra_dict["user"] = user
    if extra:
        extra_dict.update(extra)

    user_label = f" user='{user}'" if user else ""
    security_logger.warning(
        f"[SECURITY_EVENT: {event_type}] ip={client_ip}{user_label} - {detail}",
        extra=extra_dict,
    )

