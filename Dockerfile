# ── Stage 1: Build frontend ─────────────────────────────────
FROM oven/bun:1 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock* ./
RUN bun install --frozen-lockfile
COPY frontend/ .
RUN bun run build

# ── Stage 2: Final all-in-one image ─────────────────────────
FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    nginx \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY backend/ .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked

ENV PATH="/app/backend/.venv/bin:$PATH" PYTHONUNBUFFERED=1

COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY infra/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY infra/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && rm -f /etc/nginx/sites-enabled/default

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
