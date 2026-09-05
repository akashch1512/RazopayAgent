#!/bin/bash
set -e

echo "DB Connection --- Establishing . . ."

while ! nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do

    echo "DB Connection -- Failed!"

    sleep 1

    echo "DB Connection -- Retrying . . ."

done

echo "DB Connection --- Successfully Established!"

# --- Redis + Celery (same container) -----------------------------------------
# Start the broker, then the agent worker and the beat scheduler, all in the
# background, before handing off to the FastAPI server.

REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo "Redis --- Starting . . ."
mkdir -p /data
redis-server --daemonize yes --port "${REDIS_PORT}" \
    --save "60 1" --appendonly yes --dir /data

until redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping 2>/dev/null | grep -q PONG; do
    echo "Redis --- Waiting . . ."
    sleep 1
done
echo "Redis --- Successfully Established!"

CELERY="celery -A src.workers.celery_app.celery_app"

echo "Celery worker --- Starting . . ."
${CELERY} worker \
    --queues="${WEBHOOK_QUEUE_NAME:-webhook_agent}" \
    --concurrency="${CELERY_WORKER_CONCURRENCY:-4}" \
    --prefetch-multiplier=1 \
    --loglevel=info &

echo "Celery beat --- Starting . . ."
${CELERY} beat --loglevel=info &

echo "FastAPI --- Starting . . ."
exec "$@"
