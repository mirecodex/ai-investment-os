FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable


# Runtime stage: slim image, non-root, read-only app files, writable var/.
FROM python:3.11-slim-bookworm

WORKDIR /app
RUN useradd --create-home --uid 10001 invos \
    && mkdir -p /app/var \
    && chown invos:invos /app/var

COPY --from=builder /app/.venv /app/.venv
COPY data ./data
COPY prompts ./prompts
COPY eval ./eval

# Installed (non-editable) packages cannot derive the repo root, so pin
# every filesystem default explicitly.
ENV PATH="/app/.venv/bin:$PATH" \
    INVOS_REPO_ROOT=/app \
    INVOS_FIXTURES_PATH=/app/data/fixtures/idx_demo.json \
    INVOS_UNIVERSE_PATH=/app/data/universe/lq45-demo.json \
    INVOS_PROMPTS_PATH=/app/prompts \
    INVOS_GOLDEN_PATH=/app/eval/golden/decisions.json \
    INVOS_DATABASE_PATH=/app/var/investment_os.db \
    INVOS_LOG_JSON=true

USER invos
VOLUME /app/var

HEALTHCHECK --interval=60s --timeout=30s --start-period=20s --retries=3 \
    CMD ["investment-os", "health"]

CMD ["investment-os", "serve-telegram"]
