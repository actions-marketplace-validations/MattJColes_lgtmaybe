"""Tests for the .lgtmaybe.yml config loader.

Precedence: CLI inputs > repo config file > defaults.
"""

from __future__ import annotations

import pytest

from lgtmaybe.config.loader import load_config


def test_empty_file_yields_defaults(tmp_path):
    """An empty YAML file produces a valid ReviewConfig with ollama defaults."""
    cfg_file = tmp_path / ".lgtmaybe.yml"
    cfg_file.write_text("")

    cfg = load_config(config_path=cfg_file)

    assert cfg.provider == "ollama"
    assert cfg.model == "llama3"


def test_missing_file_yields_defaults(tmp_path):
    """A missing config file produces working defaults without error."""
    cfg = load_config(config_path=tmp_path / ".lgtmaybe.yml")

    assert cfg.provider == "ollama"
    assert cfg.model == "llama3"


def test_file_values_are_applied():
    """Values in the config file are reflected in the returned ReviewConfig."""
    import io

    yaml_content = "provider: anthropic\nmodel: claude-3-5-sonnet-20241022\nmin_severity: medium\n"

    cfg = load_config(config_stream=io.StringIO(yaml_content))

    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-3-5-sonnet-20241022"
    assert cfg.min_severity == "medium"


def test_cli_input_overrides_file_value():
    """An explicit CLI input takes precedence over the file's value."""
    import io

    yaml_content = "provider: openai\nmodel: gpt-4o\nmin_severity: low\n"

    cfg = load_config(config_stream=io.StringIO(yaml_content), min_severity="high")

    assert cfg.min_severity == "high"
    # File values still applied for keys not overridden
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o"


def test_cli_input_overrides_provider():
    """A CLI --provider overrides the file's provider."""
    import io

    yaml_content = "provider: openai\nmodel: gpt-4o\n"

    cfg = load_config(config_stream=io.StringIO(yaml_content), provider="anthropic")

    assert cfg.provider == "anthropic"


def test_unknown_key_in_yaml_raises():
    """An unknown key in the YAML file is rejected with a clear error (extra=forbid)."""
    import io

    yaml_content = "provider: ollama\nmodel: llama3\nunknown_key: bad\n"

    with pytest.raises(Exception, match="unknown_key|extra"):
        load_config(config_stream=io.StringIO(yaml_content))


def test_none_cli_inputs_do_not_override():
    """CLI inputs that are None (not passed) do not clobber file or default values."""
    import io

    yaml_content = "provider: openai\nmodel: gpt-4o\nmin_severity: high\n"

    # Passing None explicitly — simulates a click option that wasn't supplied
    cfg = load_config(config_stream=io.StringIO(yaml_content), provider=None, min_severity=None)

    assert cfg.provider == "openai"
    assert cfg.min_severity == "high"
