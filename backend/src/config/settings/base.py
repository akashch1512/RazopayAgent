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

    # Fernet key (urlsafe base64-encoded 32 bytes) used to encrypt Razorpay tokens at rest.
    ENCRYPTION_KEY: str = ""

    # Razorpay Partner OAuth application credentials.
    RAZORPAY_CLIENT_ID: str = ""
    RAZORPAY_CLIENT_SECRET: str = ""
    RAZORPAY_OAUTH_REDIRECT_URI: str = "http://127.0.0.1:8000/api/onboard-business/callback"
    RAZORPAY_OAUTH_SCOPE: str = "read_write"
    RAZORPAY_OAUTH_MODE: str = "test"  # `test` or `live`
    RAZORPAY_AUTH_BASE_URL: str = "https://auth.razorpay.com"
    RAZORPAY_API_BASE_URL: str = "https://api.razorpay.com"
    # Public URL Razorpay should call for sub-merchant webhook events.
    RAZORPAY_WEBHOOK_URL: str = "http://127.0.0.1:8000/api/webhooks/razorpay"
    RAZORPAY_WEBHOOK_ALERT_EMAIL: str = ""
    # Optional shared secret, used to verify deliveries when the owning business
    # (and thus its per-account secret) cannot be resolved. Leave empty to skip.
    RAZORPAY_WEBHOOK_SECRET: str = ""
    # When true, deliveries that fail signature verification are rejected (401)
    # instead of being stored with `signature_verified = false`.
    RAZORPAY_WEBHOOK_REJECT_UNVERIFIED: bool = False
    HTTP_CLIENT_TIMEOUT: int = 30

    # --- Redis (Celery broker) ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # --- Celery / task queue ---
    CELERY_BROKER_URL_OVERRIDE: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    # Run tasks inline (no broker/worker) - only for tests / local debugging.
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Dedicated queue the agent worker drains one message at a time.
    WEBHOOK_QUEUE_NAME: str = "webhook_agent"
    # Priority band handed to Redis: 0 = most urgent .. 9 = least urgent.
    WEBHOOK_PRIORITY_STEPS: int = 10
    # How many times a single case may be attempted before it is parked DEAD.
    WEBHOOK_MAX_PROCESSING_ATTEMPTS: int = 5
    WEBHOOK_RETRY_BASE_DELAY_SECONDS: int = 5
    WEBHOOK_RETRY_MAX_DELAY_SECONDS: int = 600
    # A QUEUED/PROCESSING row untouched for this long is treated as lost and re-dispatched.
    WEBHOOK_STUCK_AFTER_SECONDS: int = 900
    # How often the reconciler sweeps for starved / lost / retryable cases.
    WEBHOOK_RECONCILE_INTERVAL_SECONDS: int = 60
    WEBHOOK_RECONCILE_BATCH_SIZE: int = 500
    # Every this many seconds a case waits, its effective priority improves by 1
    # (prevents low-priority cases from starving forever behind a busy queue).
    WEBHOOK_PRIORITY_AGING_STEP_SECONDS: int = 120
    # Bounded, fast retry for the hot-path DB write before returning 503 to Razorpay.
    WEBHOOK_DB_WRITE_MAX_RETRIES: int = 3
    # How many merged webhook_event rows the agent gets as history for one case.
    RECOVERY_CASE_HISTORY_LIMIT: int = 50
    # Guardrails around the agent run inside the worker.
    WEBHOOK_TASK_SOFT_TIME_LIMIT_SECONDS: int = 240
    WEBHOOK_TASK_TIME_LIMIT_SECONDS: int = 300

    @property
    def CELERY_BROKER_URL(self) -> str:
        if self.CELERY_BROKER_URL_OVERRIDE:
            return self.CELERY_BROKER_URL_OVERRIDE
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- LangGraph recovery agent ---
    OPENAI_API_KEY: str | None = None
    AGENT_LLM_MODEL: str = "gpt-4o-mini"
    AGENT_LLM_TEMPERATURE: float = 0.2
    AGENT_LLM_TIMEOUT_SECONDS: int = 60
    # Used when a customer's phone number carries no recognisable dial code.
    DEFAULT_CUSTOMER_TIMEZONE: str = "UTC"

    # Demo stand-in for the outreach tools (call/SMS/WhatsApp/email/push) - see
    # /simulation-api. Records the action and serves it to `frontend-demo`
    # instead of hitting a real (paid) provider.
    SIMULATION_API_BASE_URL: str = "http://localhost:8001/api/v1"
    SIMULATION_API_TIMEOUT_SECONDS: int = 10

    # Razorpay MCP server - https://razorpay.com/docs/mcp-server/
    RAZORPAY_MCP_SERVER_URL: str = "https://mcp.razorpay.com/mcp"
    RAZORPAY_MCP_TRANSPORT: str = "streamable_http"
    # DEMO FALLBACK ONLY: Razorpay's legacy Key ID / Key Secret pair (from the
    # dashboard), used to authenticate the MCP session when a business has no
    # OAuth access token yet, so the agent can be exercised end-to-end before
    # onboarding completes. Never rely on this in production - every business
    # should authenticate the MCP session with its own onboarded OAuth token.
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None

    @property
    def CHECKPOINTER_DATABASE_URL(self) -> str:
        """Plain `postgresql://` DSN for psycopg (`DATABASE_URL` uses the `+asyncpg` driver)."""
        return (
            f"postgresql://{self.DB_POSTGRES_USERNAME}:{self.DB_POSTGRES_PASSWORD}@"
            f"{self.DB_POSTGRES_HOST}:{self.DB_POSTGRES_PORT}/{self.DB_POSTGRES_NAME}"
        )

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
