"""Centralized logging configuration.

Library code uses ``logging.getLogger(__name__)`` and never calls ``print``.
Scripts and the API entry point call :func:`configure_logging` once at startup.
"""

from __future__ import annotations

import logging
import logging.config
from typing import Any


def _build_config(level: str) -> dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)-8s %(name)s:%(lineno)d — %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        "loggers": {
            # Quiet noisy third-party loggers regardless of root level
            "urllib3": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "transformers": {"level": "WARNING"},
            "sentence_transformers": {"level": "WARNING"},
        },
    }


def configure_logging(level: str = "INFO") -> None:
    """Initialize logging. Idempotent — safe to call multiple times."""
    level = level.upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError(f"Invalid log level: {level}")
    logging.config.dictConfig(_build_config(level))
