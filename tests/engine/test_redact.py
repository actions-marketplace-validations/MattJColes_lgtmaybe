"""Tests for redact.py — secret scrubbing before diffs leave for the provider."""

from __future__ import annotations

from lgtmaybe.engine.redact import REDACTED_PLACEHOLDER, redact

_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
_OPENAI_KEY = "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOP"
_GITHUB_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz123456"
_API_KEY_ASSIGN = 'api_key = "supersecretvalue12345678901234567"'
_TOKEN_ASSIGN = 'token = "myverysecrettoken12345678901234567"'


def test_aws_key_redacted() -> None:
    diff = f"+AWS_ACCESS_KEY_ID={_AWS_KEY}\n"
    result = redact(diff)
    assert _AWS_KEY not in result
    assert REDACTED_PLACEHOLDER in result


def test_openai_key_redacted() -> None:
    diff = f"+OPENAI_API_KEY={_OPENAI_KEY}\n"
    result = redact(diff)
    assert _OPENAI_KEY not in result
    assert REDACTED_PLACEHOLDER in result


def test_github_token_redacted() -> None:
    diff = f"+GH_TOKEN={_GITHUB_TOKEN}\n"
    result = redact(diff)
    assert _GITHUB_TOKEN not in result
    assert REDACTED_PLACEHOLDER in result


def test_generic_api_key_assignment_redacted() -> None:
    diff = f"+{_API_KEY_ASSIGN}\n"
    result = redact(diff)
    assert "supersecretvalue" not in result
    assert REDACTED_PLACEHOLDER in result


def test_non_secret_content_preserved() -> None:
    diff = "@@ -1,3 +1,4 @@\n context\n+added normal line\n"
    result = redact(diff)
    assert "added normal line" in result
    assert REDACTED_PLACEHOLDER not in result


def test_multiple_secrets_all_redacted() -> None:
    diff = f"+AWS_KEY={_AWS_KEY}\n+OPENAI={_OPENAI_KEY}\n"
    result = redact(diff)
    assert _AWS_KEY not in result
    assert _OPENAI_KEY not in result


def test_redact_returns_string() -> None:
    assert isinstance(redact("no secrets here"), str)
