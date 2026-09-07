# syntax=docker/dockerfile:1

################################################################################
# Build stage — resolve dependencies into a self-contained virtualenv
################################################################################
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN python -m venv "$VIRTUAL_ENV"

# Dependencies resolve from pyproject alone, so this layer is rebuilt only when
# the dependency list changes rather than on every source edit.
COPY pyproject.toml ./
RUN mkdir -p src/tarakdingdung \
    && touch src/tarakdingdung/__init__.py README.md \
    && pip install .

COPY src/ ./src/
COPY database/ ./database/
COPY alembic.ini ./

# Installed editable on purpose. Both the Alembic runner and the seeder locate
# their data by walking up from the package file — five and four parents up
# respectively — so they need `alembic.ini` and `database/` to sit above
# `src/tarakdingdung`. A normal install into site-packages severs that
# relationship and both would fail at runtime.
RUN pip install --no-deps -e .

################################################################################
# Runtime stage
################################################################################
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# curl is for the container healthcheck; nothing in the app shells out.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 tarakdingdung

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh && chown -R tarakdingdung:tarakdingdung /app

# Unprivileged: the process needs no more than its own source tree, and a
# container that trades should not be able to write to it either.
USER tarakdingdung

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${TRDD_BE_HTTP_PORT:-8080}/api/version" || exit 1

ENTRYPOINT ["entrypoint.sh"]
CMD ["serve"]
