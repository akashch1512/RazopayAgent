import os
from functools import lru_cache

from src.config.settings.base import BackendBaseSettings
from src.config.settings.development import BackendDevSettings
from src.config.settings.environment import Environment
from src.config.settings.production import BackendProdSettings
from src.config.settings.staging import BackendStageSettings


class BackendSettingsFactory:
    def __init__(self, environment: str):
        self.environment = environment

    def __call__(self) -> BackendBaseSettings:
        if self.environment == Environment.DEVELOPMENT.value:
            return BackendDevSettings()
        elif self.environment == Environment.STAGING.value:
            return BackendStageSettings()
        return BackendProdSettings()


@lru_cache
def get_settings() -> BackendBaseSettings:
    return BackendSettingsFactory(environment=os.getenv("ENVIRONMENT", "DEV"))()


settings: BackendBaseSettings = get_settings()
