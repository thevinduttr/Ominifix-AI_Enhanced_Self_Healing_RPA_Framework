"""
app.infra.settings

Central place for runtime configuration. In a real deployment this can be
extended to read from environment variables, .env files, or a config server.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service metadata
    SERVICE_NAME: str = "ai_element_locator_engine"
    SERVICE_VERSION: str = "0.1.0"

    # Scoring thresholds for deciding if a locator is reliable
    HIGH_CONFIDENCE_THRESHOLD: float = 0.9
    LOW_CONFIDENCE_THRESHOLD: float = 0.6

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
