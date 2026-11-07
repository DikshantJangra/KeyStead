FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY keystead ./keystead
COPY config/keystead.example.yaml ./config/keystead.example.yaml
RUN uv sync --frozen --no-dev
# The gate runs as its own user so no coding agent on the host can read data/ or the env.
RUN useradd --system --uid 10001 --home /app keystead && mkdir -p /app/data && chown keystead /app/data
USER keystead
ENV KEYSTEAD_DATA_DIR=/app/data KEYSTEAD_CONFIG=/app/config/keystead.yaml
ENTRYPOINT ["keystead"]
CMD ["run"]
