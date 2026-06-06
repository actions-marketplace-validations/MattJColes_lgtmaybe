"""Tests for the CLI entry point and run_review logic."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from lgtmaybe.cli import build_adapters, main, run_review
from lgtmaybe.core.models import ReviewConfig
from tests.fakes import FakeEngine, FakeGitHub, FakeProvider


def _default_cfg(**overrides: object) -> ReviewConfig:
    base = {"provider": "ollama", "model": "llama3"}
    base.update(overrides)
    return ReviewConfig.model_validate(base)


class TestRunReview:
    def test_dry_run_does_not_post(self):
        """dry_run=True must not call post_review on the github gateway."""
        github = FakeGitHub()
        engine = FakeEngine(FakeProvider())
        cfg = _default_cfg()

        findings, summary = run_review(github=github, engine=engine, cfg=cfg, dry_run=True)

        assert github.posted == []

    def test_dry_run_returns_findings(self):
        """dry_run=True still returns findings and summary from the engine."""
        github = FakeGitHub()
        engine = FakeEngine(FakeProvider())
        cfg = _default_cfg()

        findings, summary = run_review(github=github, engine=engine, cfg=cfg, dry_run=True)

        assert len(findings) >= 1
        assert summary != ""

    def test_non_dry_run_posts(self):
        """Without dry_run, post_review is called exactly once."""
        github = FakeGitHub()
        engine = FakeEngine(FakeProvider())
        cfg = _default_cfg()

        run_review(github=github, engine=engine, cfg=cfg, dry_run=False)

        assert len(github.posted) == 1

    def test_non_dry_run_posts_correct_findings(self):
        """Posted findings match what the engine returned."""
        github = FakeGitHub()
        provider = FakeProvider()
        engine = FakeEngine(provider)
        cfg = _default_cfg()

        findings, summary = run_review(github=github, engine=engine, cfg=cfg, dry_run=False)

        posted_findings, posted_summary = github.posted[0]
        assert posted_findings == findings
        assert posted_summary == summary


class TestCliDryRun:
    def test_dry_run_flag_prints_findings_to_stdout(self, monkeypatch):
        """--dry-run prints JSON findings to stdout and posts nothing."""
        github = FakeGitHub()
        engine = FakeEngine(FakeProvider())

        import lgtmaybe.cli as cli_module

        monkeypatch.setattr(
            cli_module,
            "build_adapters",
            lambda cfg, runtime: (github, engine),
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "review",
                "--pr-url",
                "https://github.com/org/repo/pull/1",
                "--provider",
                "ollama",
                "--model",
                "llama3",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        assert github.posted == []
        # Output should contain structured JSON findings
        assert "canned finding" in result.output

    def test_dry_run_output_is_valid_json(self, monkeypatch):
        """--dry-run output contains parseable JSON findings."""
        github = FakeGitHub()
        engine = FakeEngine(FakeProvider())

        import lgtmaybe.cli as cli_module

        monkeypatch.setattr(
            cli_module,
            "build_adapters",
            lambda cfg, runtime: (github, engine),
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "review",
                "--pr-url",
                "https://github.com/org/repo/pull/1",
                "--provider",
                "ollama",
                "--model",
                "llama3",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        # Find and parse the JSON findings array line
        lines = result.output.strip().splitlines()
        json_line = next(line for line in lines if line.startswith("[{"))
        parsed = json.loads(json_line)
        assert isinstance(parsed, list)
        assert parsed[0]["severity"] == "low"


class TestCliBedrock:
    def test_bedrock_with_ambient_creds_does_not_require_api_key(self, monkeypatch):
        """Invoking bedrock when ambient creds are present raises no missing-key error."""
        github = FakeGitHub()
        engine = FakeEngine(FakeProvider())

        import lgtmaybe.cli as cli_module

        monkeypatch.setattr(cli_module, "build_adapters", lambda cfg, runtime: (github, engine))
        # Simulate ambient AWS creds present
        monkeypatch.setattr(cli_module, "has_ambient_aws_creds", lambda: True)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "review",
                "--pr-url",
                "https://github.com/org/repo/pull/1",
                "--provider",
                "bedrock",
                "--model",
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output


class TestBuildAdaptersSeam:
    def test_build_adapters_raises_not_implemented(self):
        """build_adapters raises NotImplementedError — wired by integration step."""
        cfg = _default_cfg()
        with pytest.raises(NotImplementedError, match="integration"):
            build_adapters(cfg, {})
