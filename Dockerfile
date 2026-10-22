FROM ghcr.io/astral-sh/uv:0.11.21 AS uv
FROM python:3.12.13-slim
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
COPY apps/api apps/api
COPY packages packages
RUN uv sync --locked --all-packages --no-dev --no-editable
RUN useradd --create-home --uid 10001 edgerunners
USER edgerunners
ENV PATH="/app/.venv/bin:$PATH" PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn edgerunners_api.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --no-access-log"]
