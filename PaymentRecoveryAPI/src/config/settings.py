import logging
import pathlib
from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent.parent.parent.resolve()


class Environment(StrEnum):
    PRODUCTION = "PROD"
    DEVELOPMENT = "DEV"
    STAGING = "STAGE"


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
    ENVIRONMENT: Environment = Environment.PRODUCTION

    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    SERVER_WORKERS: int = 1
    API_PREFIX: str = "/api"
    DOCS_URL: str = "/docs"
    OPENAPI_URL: str = "/openapi.json"
    REDOC_URL: str = "/redoc"
    OPENAPI_PREFIX: str = ""

    POSTGRES_HOST: str = "localhost"
    POSTGRES_NAME: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_SCHEMA: str = "postgresql+asyncpg"
    POSTGRES_USERNAME: str = "postgres"
    DB_POOL_SIZE: int = 10
    DB_POOL_OVERFLOW: int = 20
    DB_TIMEOUT: int = 5
    IS_DB_ECHO_LOG: bool = False
    IS_DB_FORCE_ROLLBACK: bool = False
    IS_DB_EXPIRE_ON_COMMIT: bool = False

    # Signs the self-contained onboarding `state` token (see
    # `src.api.onboarding_state`); no user-session JWTs exist yet.
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    IS_ALLOWED_CREDENTIALS: bool = True

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
    # None -> emit JSON logs unless DEBUG is on. Set explicitly to force a format.
    LOG_JSON: bool | None = None

    # Fernet key (urlsafe base64-encoded 32 bytes) used to encrypt Razorpay tokens at rest.
    ENCRYPTION_KEY: str = ""

    # Razorpay Partner OAuth application credentials.
    RAZORPAY_CLIENT_ID: str = ""
    RAZORPAY_CLIENT_SECRET: str = ""
    RAZORPAY_OAUTH_REDIRECT_URI: str = "http://127.0.0.1:8000/api/integrations/razorpay/callback"
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
    # Cache window for the "is this case already paid?" Razorpay check, so a
    # burst of outreach calls in one agent run makes at most one request.
    SETTLEMENT_CHECK_CACHE_SECONDS: int = 120
    # Outbound-HTTP retry budget for transient failures (network drop, 429, 5xx).
    HTTP_MAX_RETRY_ATTEMPTS: int = 3
    HTTP_RETRY_BASE_DELAY_SECONDS: float = 0.5
    HTTP_RETRY_MAX_DELAY_SECONDS: float = 8.0

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
    # How long a fresh webhook-triggered case waits for the customer to resolve
    # it themselves (e.g. retry a failed payment) before the agent gets involved.
    # Kept equal to `WEBHOOK_STUCK_AFTER_SECONDS` so the reconciler's staleness
    # sweep doesn't treat an intentionally-delayed case as lost too early.
    RECOVERY_GRACE_PERIOD_SECONDS: int = 900
    # How many merged webhook_event rows the agent gets as history for one case.
    RECOVERY_CASE_HISTORY_LIMIT: int = 50
    # Guardrails around the agent run inside the worker.
    WEBHOOK_TASK_SOFT_TIME_LIMIT_SECONDS: int = 240
    WEBHOOK_TASK_TIME_LIMIT_SECONDS: int = 300

    # --- Scheduled outreach ---
    SCHEDULED_ACTION_SWEEP_INTERVAL_SECONDS: int = 30
    SCHEDULED_ACTION_SWEEP_BATCH_SIZE: int = 100
    SCHEDULED_ACTION_MAX_ATTEMPTS: int = 5

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

    # The business dashboard (frontend-demo) - the OAuth callback redirects here
    # to finish onboarding instead of dead-ending in raw JSON.
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # Razorpay MCP server - https://razorpay.com/docs/mcp-server/
    RAZORPAY_MCP_SERVER_URL: str = "https://mcp.razorpay.com/mcp"
    RAZORPAY_MCP_TRANSPORT: str = "streamable_http"
    # DEMO FALLBACK ONLY: Razorpay's legacy Key ID / Key Secret pair, used to
    # authenticate the MCP session when a business has no OAuth access token yet.
    # Never rely on this in production.
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None

    # --- Drop-off detection ---
    # Razorpay has no drop-off webhook, so "customer started checkout, never
    # paid" is only discoverable by polling `GET /v1/orders` per business, one
    # business at a time on a rotation (`Business.next_dropoff_poll_at`).
    DROPOFF_SWEEP_INTERVAL_SECONDS: int = 60
    DROPOFF_POLL_INTERVAL_SECONDS: int = 900
    DROPOFF_POLL_JITTER_SECONDS: int = 60
    # An order unpaid for at least this long counts as a drop-off.
    DROPOFF_THRESHOLD_SECONDS: int = 900
    # The Orders API `from` window - must comfortably exceed
    # POLL_INTERVAL + THRESHOLD so a slow poll cycle never skips an order.
    DROPOFF_LOOKBACK_SECONDS: int = 3600
    DROPOFF_POLL_BATCH_SIZE: int = 20
    DROPOFF_MAX_ORDERS_PER_BUSINESS: int = 500

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"{self.POSTGRES_SCHEMA}://{self.POSTGRES_USERNAME}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
        )

    @property
    def CHECKPOINTER_DATABASE_URL(self) -> str:
        """Plain `postgresql://` DSN for psycopg (`DATABASE_URL` uses the `+asyncpg` driver)."""
        return (
            f"postgresql://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
        )

    @property
    def CELERY_BROKER_URL(self) -> str:
        if self.CELERY_BROKER_URL_OVERRIDE:
            return self.CELERY_BROKER_URL_OVERRIDE
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def set_backend_app_attributes(self) -> dict[str, str | bool | None]:
        """`FastAPI` constructor kwargs derived from these settings."""
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


class BackendDevSettings(BackendBaseSettings):
    DESCRIPTION: str | None = "Development Environment."
    DEBUG: bool = True
    ENVIRONMENT: Environment = Environment.DEVELOPMENT


class BackendStageSettings(BackendBaseSettings):
    DESCRIPTION: str | None = "Test Environment."
    DEBUG: bool = True
    ENVIRONMENT: Environment = Environment.STAGING


class BackendProdSettings(BackendBaseSettings):
    DESCRIPTION: str | None = "Production Environment."
    ENVIRONMENT: Environment = Environment.PRODUCTION


class BackendSettingsFactory:
    def __init__(self, environment: str) -> None:
        self.environment = environment

    def __call__(self) -> BackendBaseSettings:
        if self.environment == Environment.DEVELOPMENT.value:
            return BackendDevSettings()
        if self.environment == Environment.STAGING.value:
            return BackendStageSettings()
        return BackendProdSettings()
