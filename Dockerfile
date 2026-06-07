# Container action image, published to GHCR and pulled by action.yml.
# Builds a lean runtime: deps resolved from the lockfile, the venv put on PATH,
# and the CLI invoked directly — no uv at runtime, so cold starts stay fast.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml README.md uv.lock ./
COPY src ./src

# Bundle the azure extra so keyless Azure (Azure AD via OIDC) works out of the box.
RUN uv sync --no-dev --frozen --extra azure

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "-m", "lgtmaybe"]
