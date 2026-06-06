"""Tests for the CLI entry point and run_review logic."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from lgtmaybe.cli import build_adapters, main, run_review
from lgtmaybe.core.models import PRContext, ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import ReviewEngine
from tests.fakes import FakeEngine, FakeGitHub, FakeProvider


class _BoomEngine(ReviewEngine):
    """A ReviewEngine that always fails — used to exercise error surfacing."""

    def review(self, ctx: PRContext, cfg: ReviewConfig) -> tuple[list[ReviewFinding], str]:
        raise RuntimeError("provider exploded")


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


class TestModuleEntrypoint:
    def test_python_m_lgtmaybe_runs_the_cli_group(self):
        """`python -m lgtmaybe` (Docker ENTRYPOINT) must invoke the real CLI."""
        import lgtmaybe.__main__ as entry

        assert entry.main is main

    def test_help_lists_review_and_comment_commands(self):
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "review" in result.output
        assert "comment" in result.output


class TestErrorSurfacing:
    def _invoke(self, monkeypatch, github, engine, *, dry_run=False):
        import lgtmaybe.cli as cli_module

        monkeypatch.setattr(cli_module, "build_adapters", lambda cfg, runtime: (github, engine))
        args = [
            "review",
            "--pr-url",
            "https://github.com/org/repo/pull/1",
            "--provider",
            "ollama",
            "--model",
            "llama3",
        ]
        if dry_run:
            args.append("--dry-run")
        return CliRunner().invoke(main, args)

    def test_engine_failure_posts_comment_and_exits_nonzero(self, monkeypatch):
        github = FakeGitHub()
        result = self._invoke(monkeypatch, github, _BoomEngine())

        assert result.exit_code != 0
        assert len(github.posted) == 1
        posted_findings, posted_summary = github.posted[0]
        assert posted_findings == []
        assert "fail" in posted_summary.lower()

    def test_dry_run_failure_does_not_post(self, monkeypatch):
        github = FakeGitHub()
        result = self._invoke(monkeypatch, github, _BoomEngine(), dry_run=True)

        assert result.exit_code != 0
        assert github.posted == []

    def test_build_adapters_failure_exits_nonzero(self, monkeypatch):
        import lgtmaybe.cli as cli_module

        def boom(cfg, runtime):
            raise ValueError("GITHUB_TOKEN is required")

        monkeypatch.setattr(cli_module, "build_adapters", boom)
        result = CliRunner().invoke(
            main,
            [
                "review",
                "--pr-url",
                "https://github.com/org/repo/pull/1",
                "--provider",
                "ollama",
                "--model",
                "llama3",
            ],
        )

        assert result.exit_code != 0
        assert "GITHUB_TOKEN" in result.output


class TestParsePrUrl:
    def test_parses_owner_repo_and_number(self):
        from lgtmaybe.cli import parse_pr_url

        repo, number = parse_pr_url("https://github.com/org/my-repo/pull/42")
        assert repo == "org/my-repo"
        assert number == 42

    def test_rejects_non_pr_url(self):
        from lgtmaybe.cli import parse_pr_url

        with pytest.raises(ValueError, match="PR URL"):
            parse_pr_url("https://github.com/org/my-repo/issues/42")


class TestBuildAdapters:
    def test_builds_real_adapters_for_ollama(self, monkeypatch):
        """build_adapters returns a RestGitHubGateway + LLMReviewEngine wired from config."""
        from lgtmaybe.engine import LLMReviewEngine
        from lgtmaybe.github import RestGitHubGateway

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        cfg = _default_cfg(provider="ollama", model="llama3")
        runtime = {
            "pr_url": "https://github.com/org/repo/pull/7",
            "api_key": None,
            "api_base": None,
        }

        github, engine = build_adapters(cfg, runtime)

        assert isinstance(github, RestGitHubGateway)
        assert isinstance(engine, LLMReviewEngine)

    def test_requires_github_token(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        cfg = _default_cfg(provider="ollama", model="llama3")
        runtime = {
            "pr_url": "https://github.com/org/repo/pull/7",
            "api_key": None,
            "api_base": None,
        }

        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            build_adapters(cfg, runtime)

    def test_surfaces_missing_provider_credentials(self, monkeypatch):
        """An API-key provider with no key raises the resolver's clear error."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cfg = _default_cfg(provider="openai", model="gpt-4o")
        runtime = {
            "pr_url": "https://github.com/org/repo/pull/7",
            "api_key": None,
            "api_base": None,
        }

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            build_adapters(cfg, runtime)
