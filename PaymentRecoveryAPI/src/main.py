import contextlib
import logging
import typing

import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.endpoints import router as api_endpoint_router
from src.config.events import (
    execute_backend_server_event_handler,
    terminate_backend_server_event_handler,
)
from src.config.logging import configure_logging
from src.config.manager import settings

configure_logging()
logger = logging.getLogger(__name__)


async def _unhandled_exception_handler(request: fastapi.Request, exc: Exception) -> JSONResponse:
    """
    Turn an unhandled error into a plain JSON 500 that still carries CORS
    headers. `ServerErrorMiddleware` (which invokes this) sits *outside*
    `CORSMiddleware`, so without adding the headers here the browser sees an
    opaque "CORS request did not succeed" network failure instead of the 500.
    """
    logger.exception(f"unhandled error on {request.method} {request.url.path}: {exc!r}")
    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    if origin and (settings.ALLOWED_ORIGINS == ["*"] or origin in settings.ALLOWED_ORIGINS):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
        if settings.IS_ALLOWED_CREDENTIALS:
            headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(status_code=500, content={"detail": "Internal server error"}, headers=headers)


def initialize_backend_application() -> fastapi.FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(_: fastapi.FastAPI) -> typing.AsyncIterator[None]:
        await execute_backend_server_event_handler(backend_app=app)()
        yield
        await terminate_backend_server_event_handler(backend_app=app)()

    app = fastapi.FastAPI(
        lifespan=lifespan,
        **settings.set_backend_app_attributes,
    )  # type: ignore

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.IS_ALLOWED_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    app.include_router(
        router=api_endpoint_router,
        prefix=settings.API_PREFIX,
    )

    app.add_exception_handler(Exception, _unhandled_exception_handler)

    return app


app: fastapi.FastAPI = initialize_backend_application()
backend_app = app


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        workers=settings.SERVER_WORKERS,
        log_level=settings.LOGGING_LEVEL,
    )
