"""
Centralized logging configuration.

WHY THIS FILE EXISTS:
- Consistent logging format across the app
- Easy to toggle log levels (DEBUG, INFO, ERROR)
- Logs to both file and console for production readiness
- Structured logging makes debugging easier

WHAT IT DOES:
- Configures Python logging with JSON format
- Creates logs/ folder for storing logs
- Provides get_logger() for any module
- Automatically includes timestamps, log levels, module names

PRODUCTION TIP:
In real systems, you'd send logs to:
- CloudWatch (AWS)
- Stackdriver (GCP)
- DataDog (monitoring)
- ELK Stack (self-hosted)

For now, file logging is enough.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.utils.config import settings


# Create logs directory if it doesn't exist
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"


class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR)
    """
    level = log_level or settings.log_level

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # File handler (JSON format for parsing)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(level)
    file_formatter = JsonFormatter()
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler (readable format for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Usage in any file:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")

    Args:
        name: Module name (__name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Setup logging on import
setup_logging()
