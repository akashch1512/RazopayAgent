#!/usr/bin/env bash
#
# Build and deploy the Payment Recovery API stack (FastAPI + Celery worker +
# Celery beat + Redis) with Docker Compose.
#
# PostgreSQL is expected to run OUTSIDE this stack - configure the connection in
# .env (see .env.example). Database migrations are applied before the services
# start.
#
# Usage:
#   ./start.sh              build, migrate, (re)start everything, follow logs
#   ./start.sh --no-logs    same, but return to the shell instead of tailing
#   ./start.sh down         stop and remove the stack (Redis volume kept)
#   ./start.sh migrate      only run `alembic upgrade head`

set -euo pipefail

cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.yml"

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose -f "$COMPOSE_FILE")
elif command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose -f "$COMPOSE_FILE")
else
  echo "error: Docker Compose is not installed (need 'docker compose' or 'docker-compose')." >&2
  exit 1
fi

require_env() {
  if [[ ! -f .env ]]; then
    echo "error: .env not found in $(pwd)." >&2
    echo "       Copy .env.example to .env and fill in the external Postgres, encryption" >&2
    echo "       and Razorpay/OpenAI settings before deploying." >&2
    exit 1
  fi
}

migrate() {
  echo "==> Applying database migrations (alembic upgrade head)"
  "${DC[@]}" run --rm --no-deps api alembic upgrade head
}

case "${1:-up}" in
  down)
    "${DC[@]}" down
    exit 0
    ;;
  migrate)
    require_env
    migrate
    exit 0
    ;;
  up|--no-logs)
    ;;
  *)
    echo "error: unknown argument '$1' (expected: up | --no-logs | down | migrate)" >&2
    exit 1
    ;;
esac

require_env

echo "==> Building images"
"${DC[@]}" build

migrate

echo "==> Starting services"
"${DC[@]}" up -d

echo
"${DC[@]}" ps

echo
echo "API:   http://localhost:${BACKEND_PORT:-8000}/api/health"
echo "Logs:  ${DC[*]} logs -f"
echo "Stop:  ./start.sh down"

if [[ "${1:-up}" != "--no-logs" ]]; then
  echo
  echo "==> Following logs (Ctrl-C to detach; services keep running)"
  exec "${DC[@]}" logs -f
fi
