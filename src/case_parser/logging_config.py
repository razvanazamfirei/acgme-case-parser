"""Logging configuration for the case parser."""

from __future__ import annotations

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def setup_logging(level: LogLevel = "INFO", verbose: bool = False) -> None:
    """Set up logging configuration for the application.

    Configures the root logger with a timestamped console handler. When
    verbose is True, DEBUG level overrides the level argument. openpyxl and
    pandas loggers are always capped at WARNING to reduce noise.

    Args:
        level: Desired log level string ("DEBUG", "INFO", "WARNING", "ERROR",
            or "CRITICAL"). Ignored when verbose is True.
        verbose: If True, forces DEBUG level regardless of the level argument.
    """
    log_level = logging.DEBUG if verbose else getattr(logging, level.upper())

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Set specific logger levels
    logging.getLogger("openpyxl").setLevel(logging.WARNING)
    logging.getLogger("pandas").setLevel(logging.WARNING)
