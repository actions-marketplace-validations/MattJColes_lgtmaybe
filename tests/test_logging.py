"""Structured logging: valid JSON lines, secrets redacted."""

from __future__ import annotations

import json
import logging

from lgtmaybe.core.logging import JsonFormatter, get_logger, register_secret


def _record(msg: str, *args: object, **extra: object) -> logging.LogRecord:
    return logging.LogRecord(
        name="lgtmaybe",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=None,
    )


def test_log_line_is_valid_json() -> None:
    out = JsonFormatter().format(_record("hello %s", "world"))
    data = json.loads(out)
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
    assert data["logger"] == "lgtmaybe"


def test_secret_is_redacted() -> None:
    register_secret("sk-supersecret-123")
    out = JsonFormatter().format(_record("auth header: sk-supersecret-123"))
    assert "sk-supersecret-123" not in out
    assert "***REDACTED***" in out
    assert json.loads(out)  # still valid json after redaction


def test_extras_are_redacted_and_serialised() -> None:
    register_secret("topsecret")
    rec = _record("posting review")
    rec.repo = "lgtmaybe/lgtmaybe"
    rec.token = "topsecret"
    data = json.loads(JsonFormatter().format(rec))
    assert data["repo"] == "lgtmaybe/lgtmaybe"
    assert data["token"] == "***REDACTED***"


def test_get_logger_attaches_single_json_handler() -> None:
    logger = get_logger("lgtmaybe.test")
    get_logger("lgtmaybe.test")  # idempotent
    json_handlers = [h for h in logger.handlers if isinstance(h.formatter, JsonFormatter)]
    assert len(json_handlers) == 1
