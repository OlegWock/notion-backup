FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends cron && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV PUID=1000
ENV PGID=1000
ENV UV_CACHE_DIR=/app/.cache/uv

CMD ["./entrypoint.sh"]
