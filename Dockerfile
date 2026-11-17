# syntax=docker/dockerfile:1

# A instalação ocorre separadamente; uv e seu cache não entram na imagem final.
FROM python:3.11.18-slim-bookworm AS dependencias
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
WORKDIR /construcao
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project --no-editable --no-build

FROM python:3.11.18-slim-bookworm AS execucao
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    HOME=/tmp \
    GIT_PYTHON_REFRESH=quiet \
    DO_NOT_TRACK=1 \
    ITERATIVE_DO_NOT_TRACK=1 \
    MLFLOW_DISABLE_TELEMETRY=true \
    MLFLOW_DISABLE_AGENT_HINT=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1
WORKDIR /app
RUN groupadd --gid 10001 credito \
    && useradd --uid 10001 --gid credito --no-create-home --home-dir /tmp \
        --shell /usr/sbin/nologin credito \
    && mkdir /app/data /app/artifacts \
    && chown credito:credito /app/data /app/artifacts
COPY --from=dependencias /opt/venv /opt/venv
COPY src/ ./src/
COPY params.yaml pyproject.toml uv.lock .python-version .gitattributes ./
USER 10001:10001
ENTRYPOINT ["python", "-m", "credito_monitorado.cli"]
CMD ["run", "--config", "/app/params.yaml", "--output", "/app/artifacts", "--data-dir", "/app/data/raw"]
