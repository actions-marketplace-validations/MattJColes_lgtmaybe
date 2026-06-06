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
from lgtmaybe.config import store
from lgtmaybe.config.loader import load_config
from lgtmaybe.core.models import ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import GitHubGateway, ProviderClient, ReviewEngine
from lgtmaybe.engine import LLMReviewEngine
from lgtmaybe.github import RestGitHubGateway
from lgtmaybe.local import local_pr_context
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


def render_findings(findings: list[ReviewFinding], summary: str, *, as_json: bool) -> str:
    """Format findings for the local CLI: JSON array, or a human listing + summary."""
    if as_json:
        return json.dumps([f.model_dump(mode="json") for f in findings])

    lines: list[str] = []
    for f in findings:
        lines.append(f"{f.path}:{f.line}  [{f.severity.upper()}] {f.title}")
        lines.append(f"  {f.body}")
        if f.suggestion is not None:
            lines.append(f"  suggestion: {f.suggestion}")
        lines.append("")
    lines.append(summary)
    return "\n".join(lines)


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
        fallback_model=runtime.get("fallback_model"),
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
    "--provider",
    default=None,
    help="LLM provider (openai, anthropic, bedrock, vertex, ollama, openrouter)",
)
@click.option("--model", default=None, help="Model name understood by the chosen provider")
@click.option(
    "--fallback-model",
    default=None,
    help="Model to retry with if the primary model fails",
)
@click.option(
    "--api-key",
    default=None,
    envvar="LGTMAYBE_API_KEY",
    help="API key (not needed for bedrock/vertex with ambient creds, or ollama)",
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
    "--base",
    default=None,
    help="Base ref to diff the current branch against "
    "(default: the remote's default branch, else main)",
)
@click.option(
    "--working",
    is_flag=True,
    default=False,
    help="Review uncommitted working-tree changes instead of the branch vs base",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output findings as a JSON array instead of a human listing",
)
@click.option(
    "--config",
    "config_path",
    default=".lgtmaybe.yml",
    show_default=True,
    help="Path to a per-repo config file",
)
def review(
    provider: str | None,
    model: str | None,
    fallback_model: str | None,
    api_key: str | None,
    api_base: str | None,
    min_severity: str | None,
    max_files: int | None,
    base: str | None,
    working: bool,
    as_json: bool,
    config_path: str,
) -> None:
    """Review local git changes and print findings — no GitHub needed."""
    cfg = load_config(
        config_path=Path(config_path),
        user_config_path=store.user_config_path(),
        provider=provider,
        model=model,
        min_severity=min_severity,
        max_files=max_files,
    )

    runtime: dict[str, Any] = {
        "api_key": api_key,
        "api_base": api_base,
        "fallback_model": fallback_model,
    }

    execute_local_review(cfg, runtime, base=base, working=working, as_json=as_json)


def execute_local_review(
    cfg: ReviewConfig,
    runtime: dict[str, Any],
    *,
    base: str | None,
    working: bool,
    as_json: bool,
) -> None:
    """Review the local git diff and print findings — no GitHub involvement.

    Builds the provider straight from config/runtime (no token, no gateway),
    runs the engine over the local diff, and prints the result. Any failure
    surfaces as a clean CLI error — there is no PR to post a notice to.
    """
    try:
        auth = resolve_credentials(
            cfg.provider,
            api_key=runtime.get("api_key"),
            api_base=runtime.get("api_base") or cfg.api_base,
        )
        provider = build_provider(
            cfg.provider,
            cfg.model,
            api_key=auth.api_key,
            api_base=auth.api_base,
            fallback_model=runtime.get("fallback_model"),
        )
        engine = LLMReviewEngine(provider)
        ctx = local_pr_context(base=base, working=working)
        findings, summary = engine.review(ctx, cfg)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(render_findings(findings, summary, as_json=as_json))


def execute_review(cfg: ReviewConfig, runtime: dict[str, Any], *, dry_run: bool) -> None:
    """Build adapters, run the review, surface failures back to the PR.

    Shared by the ``review`` command and the ``action`` entrypoint.
    """
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


@main.group(name="config")
def config_cmd() -> None:
    """Manage the user-level config (set provider/model/api_base once, reuse everywhere)."""


@config_cmd.command("path")
def config_path_command() -> None:
    """Print the config file location."""
    click.echo(str(store.user_config_path()))


@config_cmd.command("show")
def config_show() -> None:
    """Print the current config."""
    text = store.as_yaml()
    click.echo(text if text else f"(no config yet at {store.user_config_path()})")


@config_cmd.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Print one config value."""
    value = store.get_key(key)
    if value is not None:
        click.echo(str(value))


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set one config value (e.g. `config set model qwen3:27b`)."""
    try:
        coerced = store.set_key(key, value)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"{key} = {coerced}")


@config_cmd.command("init")
def config_init() -> None:
    """Interactively create the config file."""
    provider = click.prompt("Provider", default="ollama")
    model = click.prompt("Model", default="llama3")
    api_base = click.prompt("API base (blank for none)", default="", show_default=False)
    try:
        store.set_key("provider", provider)
        store.set_key("model", model)
        if api_base.strip():
            store.set_key("api_base", api_base)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Wrote {store.user_config_path()}")


@main.command()
@click.option(
    "--event-path",
    envvar="GITHUB_EVENT_PATH",
    required=True,
    help="Path to the issue_comment event payload (GitHub sets GITHUB_EVENT_PATH).",
)
@click.option("--provider", default=None, help="LLM provider override")
@click.option("--model", default=None, help="Model name override")
@click.option("--fallback-model", default=None, help="Model to retry with if the primary fails")
@click.option("--api-key", default=None, envvar="LGTMAYBE_API_KEY", help="API key")
@click.option("--api-base", default=None, help="API base URL (e.g. ollama)")
@click.option("--config", "config_path", default=".lgtmaybe.yml", show_default=True)
def comment(
    event_path: str,
    provider: str | None,
    model: str | None,
    fallback_model: str | None,
    api_key: str | None,
    api_base: str | None,
    config_path: str,
) -> None:
    """Handle an issue_comment event: route a /slash command to the engine."""
    event = json.loads(Path(event_path).read_text())
    cfg = load_config(config_path=Path(config_path), provider=provider, model=model)
    runtime: dict[str, Any] = {
        "api_key": api_key,
        "api_base": api_base,
        "fallback_model": fallback_model,
    }
    execute_comment(event, cfg, runtime)


def execute_comment(event: dict[str, Any], cfg: ReviewConfig, runtime: dict[str, Any]) -> None:
    """Route an issue_comment event's slash command to the engine/provider.

    Shared by the ``comment`` command and the ``action`` entrypoint. ``runtime``
    supplies api_key/api_base/fallback_model; the PR URL is derived here.
    """
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
    runtime = {**runtime, "pr_url": f"https://github.com/{repo}/pull/{pr_number}"}

    try:
        github, engine, provider_client = build_review_context(cfg, runtime)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        dispatch(parsed, github=github, engine=engine, provider=provider_client, cfg=cfg)
    except Exception as exc:
        _post_failure(github, exc)
        raise click.ClickException(f"/{parsed.name} failed: {exc}") from exc


def pr_url_from_event(event: dict[str, Any]) -> str:
    """Build the PR URL from a pull_request(_target) event payload.

    Uses ``GITHUB_SERVER_URL`` so it works on GitHub Enterprise too.
    """
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = event["repository"]["full_name"]
    number = event["pull_request"]["number"]
    return f"{server}/{repo}/pull/{number}"


def _action_inputs() -> dict[str, str | None]:
    """Read the action's declared inputs from the ``INPUT_*`` env vars.

    GitHub sets ``INPUT_<NAME>`` for each input of a container action; empty
    strings (an unset optional input) are normalised to ``None``.
    """

    def get(name: str) -> str | None:
        value = os.environ.get(f"INPUT_{name}")
        return value or None

    return {
        "provider": get("PROVIDER"),
        "model": get("MODEL"),
        "fallback_model": get("FALLBACK_MODEL"),
        "api_key": get("API_KEY"),
        "config_path": os.environ.get("INPUT_CONFIG_PATH") or ".lgtmaybe.yml",
    }


@main.command()
def action() -> None:
    """GitHub Action entrypoint: route by event, read inputs from env.

    ``issue_comment`` routes a slash command; any other event (``pull_request``
    / ``pull_request_target``) runs a full review of the triggering PR.
    """
    inputs = _action_inputs()
    cfg = load_config(
        config_path=Path(inputs["config_path"] or ".lgtmaybe.yml"),
        provider=inputs["provider"],
        model=inputs["model"],
    )
    runtime: dict[str, Any] = {
        "api_key": inputs["api_key"],
        "api_base": None,
        "fallback_model": inputs["fallback_model"],
    }

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    if event_name == "issue_comment":
        execute_comment(event, cfg, runtime)
        return

    runtime["pr_url"] = pr_url_from_event(event)
    execute_review(cfg, runtime, dry_run=False)
