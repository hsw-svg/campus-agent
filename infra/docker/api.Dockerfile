FROM node:24-bookworm-slim AS frontend-deps

WORKDIR /web
COPY apps/web/package.json ./package.json
RUN npm install
COPY apps/web ./

FROM frontend-deps AS frontend-build

RUN npm run build

FROM python:3.13-slim AS runtime

ARG DEEPTUTOR_VERSION=1.5.8

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DEEPTUTOR_HOME=/app/runtime/deeptutor-data \
    PATH=/opt/campus-venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl nginx tini build-essential \
    && rm -f /etc/nginx/sites-enabled/default \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m venv /opt/campus-venv \
    && /opt/campus-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/campus-venv/bin/pip install --no-cache-dir \
        'alembic>=1.14,<2' \
        'beautifulsoup4>=4.12,<5' \
        'fastapi>=0.115,<1' \
        'httpx>=0.27,<1' \
        'openai>=1,<2' \
        'psycopg[binary]>=3.2,<4' \
        'pydantic-settings>=2.6,<3' \
        'python-multipart>=0.0.18,<1' \
        'openpyxl>=3.1,<4' \
        'pandas>=2.2,<3' \
        'python-docx>=1.1,<2' \
        'pymupdf>=1.24,<2' \
        'python-pptx>=1.0,<2' \
        'pgvector>=0.3,<1' \
        'sqlalchemy>=2.0,<3' \
        'websockets>=13,<17' \
        'uvicorn[standard]>=0.32,<1'

RUN python -m venv /opt/deeptutor-venv \
    && /opt/deeptutor-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/deeptutor-venv/bin/pip install --no-cache-dir "deeptutor==${DEEPTUTOR_VERSION}"

COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./alembic.ini
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY scripts/container-entrypoint.sh /usr/local/bin/container-entrypoint.sh

RUN chmod +x /usr/local/bin/container-entrypoint.sh \
    && mkdir -p /app/runtime/deeptutor-data /data/storage

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://127.0.0.1/api/health >/dev/null \
    && curl -fsS http://127.0.0.1:8001/api/v1/book/health >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/container-entrypoint.sh"]

FROM runtime AS development

COPY --from=frontend-deps /usr/local /usr/local
COPY --from=frontend-deps /web /web

ENV CAMPUS_DEV_MODE=true

FROM runtime AS production

COPY --from=frontend-build /web/dist /usr/share/nginx/html
