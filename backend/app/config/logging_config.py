import os
import logging
import json
from typing import Optional

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class JSONFormatter(logging.Formatter):
    """Formatter that outputs logs as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        return json.dumps(log_entry)


def setup_logging(
    env: Optional[str] = None,
    level: Optional[str] = None,
    json_output: Optional[bool] = None,
) -> logging.Logger:
    """
    Configure and return a root logger for the app.
    """
    # Delay import to avoid circular dependency
    try:
        from app.config.settings.main import settings

        environment = env or settings.app.ENVIRONMENT
    except Exception:
        environment = env or os.getenv("APP_ENVIRONMENT", "development")

    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    json_output = (
        json_output if json_output is not None else environment == "production"
    )

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[logging.StreamHandler()],
        force=True,
    )

    root_logger = logging.getLogger("app")

    if json_output:
        formatter = JSONFormatter()
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
        root_logger.info("Structured JSON logging enabled")

    root_logger.info(f"Logging initialized ({environment}) - level: {log_level}")
    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a named logger (child of root).
    Example:
        logger = get_logger(__name__)
    """
    return logging.getLogger(name or "app")
