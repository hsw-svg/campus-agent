#!/bin/sh

set -eu

DEEPPID=""
APIPID=""
NGINXPID=""

stop_children() {
    exit_code="${1:-0}"
    trap - EXIT INT TERM
    for pid in "$DEEPPID" "$APIPID" "$NGINXPID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    for pid in "$DEEPPID" "$APIPID" "$NGINXPID"; do
        if [ -n "$pid" ]; then
            wait "$pid" 2>/dev/null || true
        fi
    done
    exit "$exit_code"
}

trap 'stop_children 0' INT TERM
trap 'status=$?; stop_children "$status"' EXIT

mkdir -p "${DEEPTUTOR_HOME:-/app/runtime/deeptutor-data}"

# DeepTutor and the existing API intentionally keep separate configuration
# names. This mapping happens at runtime so no key is copied into the image.
LLM_BINDING="${LLM_BINDING:-openai}"
LLM_MODEL="${LLM_MODEL:-${CHAT_MODEL:-}}"
LLM_API_KEY="${LLM_API_KEY:-${CHAT_API_KEY:-}}"
LLM_HOST="${LLM_HOST:-${CHAT_BASE_URL:-}}"
LLM_API_VERSION="${LLM_API_VERSION:-}"
EMBEDDING_BINDING="${EMBEDDING_BINDING:-openai}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-${DEEPTUTOR_EMBEDDING_MODEL:-}}"
EMBEDDING_API_KEY="${EMBEDDING_API_KEY:-${CHAT_API_KEY:-}}"

if [ -z "${EMBEDDING_HOST:-}" ]; then
    EMBEDDING_HOST="${DEEPTUTOR_EMBEDDING_HOST:-}"
fi
if [ -z "$EMBEDDING_HOST" ] && [ -n "${EMBEDDING_BASE_URL:-}" ]; then
    case "$EMBEDDING_BASE_URL" in
        */embeddings) EMBEDDING_HOST="$EMBEDDING_BASE_URL" ;;
        */) EMBEDDING_HOST="${EMBEDDING_BASE_URL}embeddings" ;;
        *) EMBEDDING_HOST="${EMBEDDING_BASE_URL}/embeddings" ;;
    esac
fi

EMBEDDING_DIMENSION="${EMBEDDING_DIMENSION:-${DEEPTUTOR_EMBEDDING_DIMENSION:-${EMBEDDING_DIMENSIONS:-1024}}}"
export LLM_BINDING LLM_MODEL LLM_API_KEY LLM_HOST LLM_API_VERSION
export EMBEDDING_BINDING EMBEDDING_MODEL EMBEDDING_API_KEY EMBEDDING_HOST EMBEDDING_DIMENSION

echo "[entrypoint] starting DeepTutor on 127.0.0.1:8001"
/opt/deeptutor-venv/bin/deeptutor serve --host 127.0.0.1 --port 8001 &
DEEPPID=$!

ready=0
attempts="${DEEPTUTOR_STARTUP_ATTEMPTS:-60}"
attempt=1
while [ "$attempt" -le "$attempts" ]; do
    if ! kill -0 "$DEEPPID" 2>/dev/null; then
        echo "[entrypoint] DeepTutor exited before becoming ready" >&2
        exit 1
    fi
    if curl -fsS --max-time 2 http://127.0.0.1:8001/api/v1/book/health >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done

if [ "$ready" -ne 1 ]; then
    echo "[entrypoint] DeepTutor did not become ready after ${attempts}s" >&2
    exit 1
fi

echo "[entrypoint] DeepTutor is ready; applying database migrations"
alembic upgrade head

echo "[entrypoint] starting Campus Agent API on 127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
APIPID=$!

api_ready=0
attempt=1
while [ "$attempt" -le "$attempts" ]; do
    if ! kill -0 "$APIPID" 2>/dev/null; then
        echo "[entrypoint] Campus Agent API exited before becoming ready" >&2
        exit 1
    fi
    if curl -fsS --max-time 2 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        api_ready=1
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done

if [ "$api_ready" -ne 1 ]; then
    echo "[entrypoint] Campus Agent API did not become ready after ${attempts}s" >&2
    exit 1
fi

echo "[entrypoint] starting Nginx on port 80"
nginx -g 'daemon off;' &
NGINXPID=$!

while :; do
    for name_pid in "deeptutor:$DEEPPID" "api:$APIPID" "nginx:$NGINXPID"; do
        name="${name_pid%%:*}"
        pid="${name_pid##*:}"
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "[entrypoint] critical service exited: $name" >&2
            exit 1
        fi
    done
    sleep 1
done
