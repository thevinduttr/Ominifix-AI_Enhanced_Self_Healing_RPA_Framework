"""
app.infra.logging_config

Simple logging configuration used by the service. This keeps all log formatting
in a single place so it can be updated without touching business logic.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.infra.settings import settings


def configure_logging(log_file: str | Path = "logs/locator_engine.log") -> None:
    """
    Configure root logger with both console and rotating file handlers.
    This function is idempotent; you can call it safely from multiple modules.
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    if logger.handlers:
        # Already configured
        return

    logger.setLevel(settings.LOG_LEVEL)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.LOG_LEVEL)
    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(settings.LOG_LEVEL)
    file_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
