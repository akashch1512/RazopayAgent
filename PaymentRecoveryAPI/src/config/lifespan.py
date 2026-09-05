import logging
import typing

import fastapi

from src.config.logging import configure_logging
from src.repository.engine_events import dispose_db_connection, initialize_db_connection

logger = logging.getLogger(__name__)


def execute_backend_server_event_handler(backend_app: fastapi.FastAPI) -> typing.Any:
    async def launch_backend_server_events() -> None:
        # Re-assert our handler: uvicorn installs its own logging config when the
        # server boots, which can be after `src.main` import time.
        configure_logging(force=True)
        logger.info("backend server starting: initializing database connection")
        await initialize_db_connection(backend_app=backend_app)
        logger.info("backend server started")

    return launch_backend_server_events


def terminate_backend_server_event_handler(backend_app: fastapi.FastAPI) -> typing.Any:
    async def stop_backend_server_events() -> None:
        logger.info("backend server shutting down: disposing database connection")
        try:
            await dispose_db_connection(backend_app=backend_app)
        except Exception:
            logger.exception("failed to dispose the database connection during shutdown")

    return stop_backend_server_events
