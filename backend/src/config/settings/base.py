import logging
import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent.parent.parent.parent.resolve()


class BackendBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    TITLE: str = "Razopay Agent API"
    VERSION: str = "0.1.0"
    TIMEZONE: str = "UTC"
    DESCRIPTION: str | None = None
    DEBUG: bool = False

    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    SERVER_WORKERS: int = 1
    API_PREFIX: str = "/api"
    DOCS_URL: str = "/docs"
    OPENAPI_URL: str = "/openapi.json"
    REDOC_URL: str = "/redoc"
    OPENAPI_PREFIX: str = ""

    DB_POSTGRES_HOST: str = "localhost"
    DB_POSTGRES_NAME: str = "postgres"
    DB_POSTGRES_PASSWORD: str = "postgres"
    DB_POSTGRES_PORT: int = 5432
    DB_POSTGRES_SCHEMA: str = "postgresql+asyncpg"
    DB_POSTGRES_USERNAME: str = "postgres"
    DB_POOL_SIZE: int = 10
    DB_POOL_OVERFLOW: int = 20
    DB_TIMEOUT: int = 5
    IS_DB_ECHO_LOG: bool = False
    IS_DB_FORCE_ROLLBACK: bool = False
    IS_DB_EXPIRE_ON_COMMIT: bool = False

    API_TOKEN: str | None = None
    AUTH_TOKEN: str | None = None
    JWT_TOKEN_PREFIX: str = "Bearer"
    JWT_SECRET_KEY: str = "change-me"
    JWT_SUBJECT: str = "access"
    JWT_MIN: int = 60
    JWT_HOUR: int = 1
    JWT_DAY: int = 1
    IS_ALLOWED_CREDENTIALS: bool = True

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"{self.DB_POSTGRES_SCHEMA}://{self.DB_POSTGRES_USERNAME}:"
            f"{self.DB_POSTGRES_PASSWORD}@{self.DB_POSTGRES_HOST}:"
            f"{self.DB_POSTGRES_PORT}/{self.DB_POSTGRES_NAME}"
        )

    @property
    def JWT_ACCESS_TOKEN_EXPIRATION_TIME(self) -> int:
        return self.JWT_MIN * self.JWT_HOUR * self.JWT_DAY

    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",  # React default port
        "http://0.0.0.0:3000",
        "http://127.0.0.1:3000",  # React docker port
        "http://127.0.0.1:3001",
        "http://localhost:5173",  # Qwik default port
        "http://0.0.0.0:5173",
        "http://127.0.0.1:5173",  # Qwik docker port
        "http://127.0.0.1:5174",
    ]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]

    LOGGING_LEVEL: int = logging.INFO
    LOGGERS: tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

    HASHING_ALGORITHM_LAYER_1: str = "bcrypt"
    HASHING_ALGORITHM_LAYER_2: str = "argon2"
    HASHING_SALT: str = ""
    JWT_ALGORITHM: str = "HS256"

    @property
    def set_backend_app_attributes(self) -> dict[str, str | bool | None]:
        """
        Set all `FastAPI` class' attributes with the custom values defined in `BackendBaseSettings`.
        """
        return {
            "title": self.TITLE,
            "version": self.VERSION,
            "debug": self.DEBUG,
            "description": self.DESCRIPTION,
            "docs_url": self.DOCS_URL,
            "openapi_url": self.OPENAPI_URL,
            "redoc_url": self.REDOC_URL,
            "openapi_prefix": self.OPENAPI_PREFIX,
        }
