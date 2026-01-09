"""
Logging configuration for the application.

Supports per-module log levels via environment variables:
- LOG_LEVEL: Global log level (default: INFO)
- LOG_FORMAT: Log format - simple or structured (default: structured)
- LOG_LEVEL_<MODULE>: Per-module override (e.g., LOG_LEVEL_AI_CLIENT=DEBUG)
"""

import logging
import sys

if sys.version_info >= (3, 11):
    from typing import TYPE_CHECKING
else:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from app.config import Settings


# Module name mapping: settings field suffix -> logger name
MODULE_LOGGERS = {
    "ai_client": "app.services.ai_client",
    "pipeline": "app.services.pipeline",
    "transcriber": "app.services.transcriber",
    "cleaner": "app.services.cleaner",
    "chunker": "app.services.chunker",
    "summarizer": "app.services.summarizer",
}


class StructuredFormatter(logging.Formatter):
    """
    Structured log formatter for easy parsing.

    Format: timestamp | level | logger | message
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in structured format."""
        # Shorten logger name for readability
        logger_name = record.name
        if logger_name.startswith("app.services."):
            logger_name = logger_name.replace("app.services.", "")
        elif logger_name.startswith("app.api."):
            logger_name = logger_name.replace("app.api.", "api.")
        elif logger_name.startswith("app."):
            logger_name = logger_name.replace("app.", "")

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        message = (
            f"{timestamp} | "
            f"{record.levelname:8} | "
            f"{logger_name:15} | "
            f"{record.getMessage()}"
        )

        # Add exception traceback if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(settings: "Settings") -> None:
    """
    Configure logging based on settings.

    Args:
        settings: Application settings with log configuration
    """
    # Parse root log level
    root_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Choose formatter
    if settings.log_format == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(root_level)
    root_logger.addHandler(handler)

    # Configure per-module loggers
    _configure_module_loggers(settings, root_level)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def _configure_module_loggers(settings: "Settings", default_level: int) -> None:
    """
    Configure individual module log levels.

    Args:
        settings: Application settings
        default_level: Default log level to use
    """
    for module_key, logger_name in MODULE_LOGGERS.items():
        # Get level from settings (e.g., settings.log_level_ai_client)
        level_str = getattr(settings, f"log_level_{module_key}", None)

        if level_str:
            level = getattr(logging, level_str.upper(), default_level)
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
