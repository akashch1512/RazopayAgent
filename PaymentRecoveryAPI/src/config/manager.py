import os
from functools import lru_cache

from src.config.settings import BackendBaseSettings, BackendSettingsFactory


@lru_cache
def get_settings() -> BackendBaseSettings:
    return BackendSettingsFactory(environment=os.getenv("ENVIRONMENT", "DEV"))()


settings: BackendBaseSettings = get_settings()
