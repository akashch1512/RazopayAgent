"""
Process-wide logging setup for both entry points (the FastAPI/uvicorn process
and the Celery worker/beat process).

The flow is deliberately boring and container-native::

    FastAPI / Celery  ->  `logging`  ->  stdout  ->  Docker / platform  ->  log store

Every module logs through the stdlib `logging` module (``logging.getLogger(__name__)``);
this module is the only place that attaches a handler. One `StreamHandler` on
stdout, JSON in deployed environments (so the hosting platform can index fields)
and human-readable text locally. No files, no rotation - the platform owns
retention.
"""

import datetime
import json
import logging
import sys
import typing

from src.config.manager import settings

_CONFIGURED = False

# Third-party loggers that are chatty at INFO and rarely useful outside debugging.
_NOISY_LOGGERS: dict[str, int] = {
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "asyncio": logging.WARNING,
    "aiosqlite": logging.WARNING,
    "multipart": logging.WARNING,
}

_RESERVED_RECORD_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JSONLogFormatter(logging.Formatter):
    """One JSON object per line - the shape container log platforms expect."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, typing.Any] = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, tz=datetime.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        # Anything passed via `logger.info(..., extra={...})` rides along as a field.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str, ensure_ascii=False)


def _use_json() -> bool:
    override = getattr(settings, "LOG_JSON", None)
    if override is not None:
        return bool(override)
    return not settings.DEBUG


def _build_formatter() -> logging.Formatter:
    if _use_json():
        return JSONLogFormatter()
    return logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def configure_logging(*, force: bool = False) -> None:
    """
    Point the root logger at stdout with our formatter. Idempotent - safe to call
    from `main.py` import, the FastAPI lifespan, and the Celery `setup_logging`
    signal without stacking handlers.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    level = settings.LOGGING_LEVEL

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_build_formatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn installs its own handlers; route its records through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "gunicorn.error", "gunicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    for name, noisy_level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(noisy_level)

    _CONFIGURED = True
    logging.getLogger(__name__).debug(
        "logging configured", extra={"json": _use_json(), "level": logging.getLevelName(level)}
    )
