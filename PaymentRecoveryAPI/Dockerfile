FROM python:3.12-slim

WORKDIR /usr/backend

# Set up Python behaviour
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/backend/.venv/bin:$PATH"

EXPOSE 8000

RUN apt-get update \
  && apt-get -y install --no-install-recommends netcat-openbsd gcc redis-server \
  && apt-get clean

# Redis + Celery run inside this same container (started by entrypoint.sh
# before uvicorn), so the app talks to a local broker by default.
ENV REDIS_HOST=127.0.0.1
ENV REDIS_PORT=6379

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
  && uv sync --frozen --no-dev

COPY . .

RUN chmod +x /usr/backend/entrypoint.sh

# Execute entrypoint.sh
ENTRYPOINT ["/usr/backend/entrypoint.sh"]

# Start up the backend server
CMD uvicorn src.main:backend_app --host 0.0.0.0 --port 8000
