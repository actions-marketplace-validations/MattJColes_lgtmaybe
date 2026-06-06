"""CLI entry point for lgtmaybe.

The command loads config (applying CLI precedence), resolves runtime options,
then delegates to ``run_review`` which is injected with ports — testable with
fakes, and wired with real adapters in the integration step.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import click

from lgtmaybe.config.loader import load_config
from lgtmaybe.core.models import ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import GitHubGateway, ReviewEngine


def has_ambient_aws_creds() -> bool:
    """Return True when AWS credentials appear to be available in the environment.

    Detection seam — real resolution belongs to Track A's credential resolver,
    wired in the integration step.  Here we check the most common indicators
    so the CLI can branch without requiring an explicit --api-key for bedrock.
    """
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_ROLE_ARN")
        or os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
        or os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        or Path(os.path.expanduser("~/.aws/credentials")).exists()
    )


def has_ambient_gcp_creds() -> bool:
    """Return True when GCP Application Default Credentials appear to be available.

    Detection seam — real resolution is Track A's responsibility.
    """
    adc_path = Path(os.path.expanduser("~/.config/gcloud/application_default_credentials.json"))
    return bool(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or adc_path.exists()
    )


def build_adapters(
    cfg: ReviewConfig, runtime: dict[str, Any]
) -> tuple[GitHubGateway, ReviewEngine]:
    """Construct real adapters from config and runtime options.

    Raises NotImplementedError — wired in the integration step (step 3).
    Tests override this via monkeypatch to inject fakes.
    """
    raise NotImplementedError(
        "build_adapters is wired in the integration step. Inject fakes in tests via monkeypatch."
    )


def run_review(
    *,
    github: GitHubGateway,
    engine: ReviewEngine,
    cfg: ReviewConfig,
    dry_run: bool,
) -> tuple[list[ReviewFinding], str]:
    """Core review pipeline — pure function over injected ports.

    Fetches PR context, runs the engine, and optionally posts the review.
    Returns (findings, summary) in all cases so callers can inspect output.
    """
    ctx = github.get_pr_context()
    findings, summary = engine.review(ctx, cfg)

    if not dry_run:
        github.post_review(findings, summary)

    return findings, summary


@click.group()
def main() -> None:
    """lgtmaybe — provider-agnostic PR reviewer."""


@main.command()
@click.option(
    "--pr-url",
    required=True,
    help="Full GitHub PR URL, e.g. https://github.com/org/repo/pull/42",
)
@click.option(
    "--provider",
    default=None,
    help="LLM provider (openai, anthropic, bedrock, vertex, ollama, openrouter)",
)
@click.option("--model", default=None, help="Model name understood by the chosen provider")
@click.option(
    "--api-key",
    default=None,
    envvar="LGTMAYBE_API_KEY",
    help="API key (not needed for bedrock/vertex with ambient creds)",
)
@click.option(
    "--api-base", default=None, help="API base URL (useful for ollama: http://localhost:11434)"
)
@click.option(
    "--min-severity",
    default=None,
    type=click.Choice(["info", "low", "medium", "high", "critical"]),
    help="Minimum severity to report",
)
@click.option("--max-files", default=None, type=int, help="Maximum number of files to review")
@click.option(
    "--config",
    "config_path",
    default=".lgtmaybe.yml",
    show_default=True,
    help="Path to config file",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print findings to stdout; do not post to GitHub",
)
def review(
    pr_url: str,
    provider: str | None,
    model: str | None,
    api_key: str | None,
    api_base: str | None,
    min_severity: str | None,
    max_files: int | None,
    config_path: str,
    dry_run: bool,
) -> None:
    """Review a pull request and post inline comments + a summary."""
    cfg = load_config(
        config_path=Path(config_path),
        provider=provider,
        model=model,
        min_severity=min_severity,
        max_files=max_files,
    )

    runtime: dict[str, Any] = {
        "pr_url": pr_url,
        "api_key": api_key,
        "api_base": api_base,
    }

    github, engine = build_adapters(cfg, runtime)

    findings, summary = run_review(github=github, engine=engine, cfg=cfg, dry_run=dry_run)

    if dry_run:
        click.echo(f"[dry-run] {summary}")
        click.echo(json.dumps([f.model_dump(mode="json") for f in findings]))
