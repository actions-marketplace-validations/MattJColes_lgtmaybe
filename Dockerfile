# Container action image (published to GHCR). The CLI track wires the real
# entrypoint; this builds the skeleton into a runnable image today.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --no-dev

ENTRYPOINT ["uv", "run", "python", "-m", "lgtmaybe"]
