#!/bin/bash
#
# One container runs Redis (broker), the Celery agent worker, the Celery beat
# scheduler and the FastAPI server. Beat is NOT optional - the reconciler it
# schedules (`recovery-cases-reconcile`, every 60s) is what re-dispatches cases
# stuck in PROCESSING/QUEUED, retries FAILED ones and ages priority. Without it
# stuck cases sit at "running now" forever.
#
# Every one of the four must come up and stay up. If any fails its startup
# readiness check, this script kills whatever it already started and exits
# non-zero so the container never reaches a half-running state. After startup
# the same processes are supervised: if any exits, the container goes down
# (non-zero) and `restart: unless-stopped` brings it back as a whole.

set -euo pipefail

PIDS=()
# Seconds to wait for each component to become ready before giving up.
READY_TIMEOUT="${STARTUP_READY_TIMEOUT:-60}"

shutdown() {
    echo "entrypoint --- stopping all supervised processes"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}

die() {
    echo "entrypoint --- FATAL: $*" >&2
    shutdown
    exit 1
}

trap shutdown SIGTERM SIGINT

# require_up <name> <pid> <check-cmd...>
# Polls <check-cmd> until it succeeds; fails hard if the process dies or the
# check never passes within READY_TIMEOUT.
require_up() {
    local name="$1" pid="$2"
    shift 2
    local waited=0
    until "$@" >/dev/null 2>&1; do
        kill -0 "$pid" 2>/dev/null || die "${name} process exited during startup"
        [ "$waited" -ge "$READY_TIMEOUT" ] && die "${name} not ready after ${READY_TIMEOUT}s"
        sleep 2
        waited=$((waited + 2))
    done
    echo "${name} --- ready"
}

# --- Postgres reachable --------------------------------------------------
echo "DB Connection --- Establishing . . ."
db_waited=0
until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}" >/dev/null 2>&1; do
    [ "$db_waited" -ge "$READY_TIMEOUT" ] && die "Postgres ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432} unreachable after ${READY_TIMEOUT}s"
    echo "DB Connection -- Failed! Retrying . . ."
    sleep 2
    db_waited=$((db_waited + 2))
done
echo "DB Connection --- Successfully Established!"

# --- Redis -------------------------------------------------------------
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo "Redis --- Starting . . ."
mkdir -p /data
redis-server --port "${REDIS_PORT}" --save "60 1" --appendonly yes --dir /data --daemonize no &
PIDS+=($!)
require_up "Redis" "${PIDS[-1]}" \
    bash -c "redis-cli -h '${REDIS_HOST}' -p '${REDIS_PORT}' ping | grep -q PONG"

# --- Celery worker ----------------------------------------------------
CELERY="celery -A src.workers.celery_app.celery_app"

echo "Celery worker --- Starting . . ."
${CELERY} worker \
    --queues="${WEBHOOK_QUEUE_NAME:-webhook_agent}" \
    --concurrency="${CELERY_WORKER_CONCURRENCY:-4}" \
    --prefetch-multiplier=1 \
    --loglevel=info &
PIDS+=($!)
require_up "Celery worker" "${PIDS[-1]}" \
    bash -c "${CELERY} inspect ping -t 5 | grep -q pong"

# --- Celery beat ----------------------------------------------------
echo "Celery beat --- Starting . . ."
# Persist the schedule on the /data volume so a restart doesn't re-fire
# everything (and doesn't fight a read-only working dir).
${CELERY} beat \
    --schedule=/data/celerybeat-schedule \
    --loglevel=info &
PIDS+=($!)
# Beat has no ping endpoint; it writes its schedule db shortly after boot.
require_up "Celery beat" "${PIDS[-1]}" \
    bash -c "test -e /data/celerybeat-schedule -o -e /data/celerybeat-schedule.db"

# --- FastAPI (the passed CMD) --------------------------------------
echo "FastAPI --- Starting . . ."
"$@" &
PIDS+=($!)
require_up "FastAPI" "${PIDS[-1]}" \
    bash -c "python -c \"import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)\""

echo "entrypoint --- all components up (Redis, Celery worker, Celery beat, FastAPI)"

# --- Supervise ----------------------------------------------------
# The moment any one exits, take the container down so it restarts whole.
set +e
wait -n
status=$?
set -e
echo "entrypoint --- a supervised process exited (status ${status}); stopping container"
shutdown
exit "${status:-1}"
