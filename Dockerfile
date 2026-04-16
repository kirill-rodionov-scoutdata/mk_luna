# ── Stage 1: dependency resolution ──────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN pip install uv

WORKDIR /app
COPY pyproject.toml .

# Install deps into an isolated virtualenv
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -e ".[dev]"

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
