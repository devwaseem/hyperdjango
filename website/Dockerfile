ARG PYTHON_VERSION=3.14
ARG APP_HOME="/app"

# --------------------------------------------------------------
# Build frontend asset files
# --------------------------------------------------------------
FROM node:22-slim AS frontend_builder

ARG APP_HOME

ENV APP_HOME="$APP_HOME"
ENV VITE_APP_OUTPUT_DIR="dist"

WORKDIR "$APP_HOME"

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN npm run build

# --------------------------------------------------------------
# Builder
# --------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-trixie AS builder-base

ARG PYTHON_VERSION
ARG APP_HOME

ENV APP_HOME="$APP_HOME"
ENV VIRTUAL_ENV_PATH="$APP_HOME/.venv"
ENV DIST_DIR="$APP_HOME/dist/"
ENV UV_PROJECT_ENVIRONMENT="${VIRTUAL_ENV_PATH}"
ENV UV_LINK_MODE=copy
ENV UV_PYTHON=/usr/local/bin/python
ENV VITE_APP_OUTPUT_DIR="dist"

WORKDIR "$APP_HOME"

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ── Production dependencies ─────────────────────────────────────────────
FROM builder-base AS production-deps

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --no-install-project --compile-bytecode

# ── CI dependencies ─────────────────────────────────────────────────────
FROM production-deps AS ci-deps

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev \
    --group test --group code-checks --group types \
    --no-install-project --compile-bytecode


# ── Production Base ─────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-trixie AS production-base

ARG APP_HOME
ENV APP_HOME="$APP_HOME"
ENV VIRTUAL_ENV_PATH="$APP_HOME/.venv"
ENV DIST_DIR="$APP_HOME/dist/"
ENV VITE_APP_OUTPUT_DIR="dist"

WORKDIR "$APP_HOME"

RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq5 \
    libmagic1 \
    gettext \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*


COPY . .

COPY --from=production-deps ${VIRTUAL_ENV_PATH} ${VIRTUAL_ENV_PATH}

COPY --from=frontend_builder ${APP_HOME}/dist ${APP_HOME}/dist

RUN chmod +x "${APP_HOME}/uvicorn.sh" \
 && python -m compileall -q "${APP_HOME}"

# ── Production build ────────────────────────────────────────────────────
FROM gcr.io/distroless/cc-debian13:nonroot AS production

ARG APP_HOME
ENV APP_HOME="$APP_HOME"
ENV VIRTUAL_ENV_PATH="$APP_HOME/.venv"
ENV DIST_DIR="$APP_HOME/dist/"
ENV VITE_APP_OUTPUT_DIR="dist"
ENV PATH="/$APP_HOME/.venv/bin:$PATH"

ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1

WORKDIR "$APP_HOME"

COPY --from=production-base /usr/local /usr/local
COPY --from=production-base /usr/lib /usr/lib
COPY --from=production-base /lib /lib
COPY --from=production-base /etc/ssl/certs /etc/ssl/certs
COPY --from=production-base /usr/bin/gettext /usr/bin/gettext
COPY --from=production-base --chown=nonroot:nonroot "${APP_HOME}" "${APP_HOME}"


# ── CI build ────────────────────────────────────────────────────────────
FROM production AS ci

COPY --from=ci-deps "${VIRTUAL_ENV_PATH}" "${VIRTUAL_ENV_PATH}"
