"""CLI entry point for lgtmaybe.

The command loads config (applying CLI precedence), resolves runtime options,
then delegates to ``run_review`` which is injected with ports — testable with
fakes, and wired with real adapters in the integration step.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import click

from lgtmaybe.cli.slash import dispatch, parse_command
from lgtmaybe.config.loader import load_config
from lgtmaybe.core.models import ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import GitHubGateway, ProviderClient, ReviewEngine
from lgtmaybe.engine import LLMReviewEngine
from lgtmaybe.github import RestGitHubGateway
from lgtmaybe.providers.credentials import resolve_credentials
from lgtmaybe.providers.factory import build_provider

_PR_URL_RE = re.compile(r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)")


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


def parse_pr_url(pr_url: str) -> tuple[str, int]:
    """Parse a GitHub PR URL into ("owner/repo", pr_number).

    Raises ValueError with a clear message for anything that is not a PR URL.
    """
    match = _PR_URL_RE.search(pr_url)
    if match is None:
        raise ValueError(
            f"Could not parse a GitHub PR URL from {pr_url!r}. "
            "Expected something like https://github.com/org/repo/pull/42"
        )
    return f"{match['owner']}/{match['repo']}", int(match["number"])


def build_review_context(
    cfg: ReviewConfig, runtime: dict[str, Any]
) -> tuple[RestGitHubGateway, LLMReviewEngine, ProviderClient]:
    """Construct the gateway, engine, and provider from config + runtime.

    Resolves provider credentials (ambient for cloud, key for the rest), builds a
    litellm-backed provider, and points a REST gateway at the parsed PR. Raises
    ValueError with an actionable message when a token or credential is missing.
    The provider is returned too so slash commands (/ask, /describe) can use it
    directly.
    """
    repo, pr_number = parse_pr_url(runtime["pr_url"])

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError(
            "GITHUB_TOKEN is required to fetch the PR and post the review. "
            "Set it in the environment (the GitHub Action provides it automatically)."
        )

    auth = resolve_credentials(
        cfg.provider,
        api_key=runtime.get("api_key"),
        api_base=runtime.get("api_base"),
    )
    provider = build_provider(
        cfg.provider,
        cfg.model,
        api_key=auth.api_key,
        api_base=auth.api_base,
    )

    github = RestGitHubGateway(repo=repo, pr_number=pr_number, token=token)
    engine = LLMReviewEngine(provider)
    return github, engine, provider


def build_adapters(
    cfg: ReviewConfig, runtime: dict[str, Any]
) -> tuple[GitHubGateway, ReviewEngine]:
    """Construct the real GitHub gateway and review engine from config + runtime."""
    github, engine, _provider = build_review_context(cfg, runtime)
    return github, engine


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

    # Adapter construction can fail before we have any way to post (bad URL,
    # missing token/credentials). Surface those as a clean CLI error.
    try:
        github, engine = build_adapters(cfg, runtime)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    # From here we have a gateway, so any failure is surfaced back to the PR as
    # a short comment rather than failing silently — then we exit non-zero.
    try:
        findings, summary = run_review(github=github, engine=engine, cfg=cfg, dry_run=dry_run)
    except Exception as exc:
        if not dry_run:
            _post_failure(github, exc)
        raise click.ClickException(f"review failed: {exc}") from exc

    if dry_run:
        click.echo(f"[dry-run] {summary}")
        click.echo(json.dumps([f.model_dump(mode="json") for f in findings]))


def _post_failure(github: GitHubGateway, exc: Exception) -> None:
    """Post a short failure notice to the PR; never raise from here."""
    notice = f"⚠️ lgtmaybe review failed: {exc}"
    try:
        github.post_review([], notice)
    except Exception:
        # Posting the failure notice itself failed — nothing more we can do;
        # the original error is still surfaced by the caller's ClickException.
        pass


@main.command()
@click.option(
    "--event-path",
    envvar="GITHUB_EVENT_PATH",
    required=True,
    help="Path to the issue_comment event payload (GitHub sets GITHUB_EVENT_PATH).",
)
@click.option("--provider", default=None, help="LLM provider override")
@click.option("--model", default=None, help="Model name override")
@click.option("--api-key", default=None, envvar="LGTMAYBE_API_KEY", help="API key")
@click.option("--api-base", default=None, help="API base URL (e.g. ollama)")
@click.option("--config", "config_path", default=".lgtmaybe.yml", show_default=True)
def comment(
    event_path: str,
    provider: str | None,
    model: str | None,
    api_key: str | None,
    api_base: str | None,
    config_path: str,
) -> None:
    """Handle an issue_comment event: route a /slash command to the engine."""
    event = json.loads(Path(event_path).read_text())

    parsed = parse_command(event.get("comment", {}).get("body", ""))
    if parsed is None:
        click.echo("No lgtmaybe slash command found; ignoring.")
        return

    issue = event.get("issue", {})
    if "pull_request" not in issue:
        click.echo("Comment is not on a pull request; ignoring.")
        return

    repo = event["repository"]["full_name"]
    pr_number = issue["number"]
    pr_url = f"https://github.com/{repo}/pull/{pr_number}"

    cfg = load_config(
        config_path=Path(config_path),
        provider=provider,
        model=model,
    )
    runtime: dict[str, Any] = {"pr_url": pr_url, "api_key": api_key, "api_base": api_base}

    try:
        github, engine, provider_client = build_review_context(cfg, runtime)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        dispatch(parsed, github=github, engine=engine, provider=provider_client, cfg=cfg)
    except Exception as exc:
        _post_failure(github, exc)
        raise click.ClickException(f"/{parsed.name} failed: {exc}") from exc
