"""
Logging configuration for the silent package.

This module provides a centralized logging setup following Python best practices:
- Hierarchical logger names (silent.*)
- Explicit logging configuration from function inputs
- Structured formatting with timestamps, levels, and module names
- Support for both console and file logging
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Literal

# Log level type
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Package logger name
PACKAGE_LOGGER_NAME = "silent"


@dataclass
class LoggingSettings:
    log_level: LogLevel = "INFO"
    verbose: bool = False
    log_format: str = DEFAULT_LOG_FORMAT
    log_date_format: str = DEFAULT_DATE_FORMAT
    log_file: str | None = None


def _is_logging_configured() -> bool:
    """
    Return True if the root logger (or any of its ancestors) has handlers.

    This mirrors the behavior of ``logging.Logger.hasHandlers()`` on Python
    3.2+, while remaining defensive for older versions.
    """
    root_logger = logging.getLogger()

    if hasattr(root_logger, "hasHandlers"):
        return root_logger.hasHandlers()  # type: ignore[no-any-return]

    # Fallback for very old Python versions
    return bool(root_logger.handlers)


def _get_log_level(settings: LoggingSettings) -> int:
    """
    Get the log level from logging settings.

    Returns:
        int: Logging level constant (e.g., logging.INFO)
    """
    level_str = settings.log_level.upper()

    # Verbose mode overrides to DEBUG
    if settings.verbose:
        return logging.DEBUG

    # Map string levels to logging constants
    level_map: dict[str, int] = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    return level_map.get(level_str, logging.INFO)


def setup_logger(settings: LoggingSettings) -> None:
    """
    Configure logging for the ``silent`` package if needed.

    Behavior:
    - If application-level logging is already configured (i.e. the root logger
      has handlers), the package will not modify global logging configuration
      and will only attach a ``NullHandler`` to avoid "No handlers could be
      found" warnings.
    - If logging is not yet configured, ``silent`` sets up its own console and
      optional file handlers based on explicit settings.
    """
    logger = logging.getLogger(PACKAGE_LOGGER_NAME)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return

    # If the application has already configured logging, do not change it.
    # Attach a NullHandler so library usage does not emit "No handlers could
    # be found" warnings, while still allowing records to propagate.
    if _is_logging_configured():
        logger.addHandler(logging.NullHandler())
        return

    # No global logging configuration detected; configure package-local
    # handlers using explicit settings.
    level = _get_log_level(settings)
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    log_format = settings.log_format
    log_date_format = settings.log_date_format
    console_formatter = logging.Formatter(
        fmt=log_format,
        datefmt=log_date_format,
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if explicitly configured)
    log_file = settings.log_file
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            fmt=log_format,
            datefmt=log_date_format,
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to the root logger when we fully manage handlers to
    # avoid duplicate messages.
    logger.propagate = False


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance for a module.

    This function follows the best practice of using module names as logger names.
    The logger name will be 'silent.module_name' for better organization.

    Args:
        name: Name of the logger. If None, uses the calling module's name.
              Should typically be __name__ when called from a module.

    Returns:
        logging.Logger: Configured logger instance

    Examples:
        >>> # In a module file (e.g., orchestrator.py)
        >>> from silent.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing video...")

        >>> # Or with explicit name
        >>> logger = get_logger("silent.orchestrator")
    """
    if name is None:
        # Try to get the calling module's name
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", PACKAGE_LOGGER_NAME)
        else:
            name = PACKAGE_LOGGER_NAME
    elif not name.startswith(PACKAGE_LOGGER_NAME):
        # Ensure logger name starts with package name for hierarchy
        name = f"{PACKAGE_LOGGER_NAME}.{name}" if name else PACKAGE_LOGGER_NAME

    return logging.getLogger(name)


def set_log_level(level: LogLevel | int) -> None:
    """
    Set the log level for all silent loggers.

    Args:
        level: Log level as string ("DEBUG", "INFO", etc.) or logging constant
    """
    if isinstance(level, str):
        level_map: dict[str, int] = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        level = level_map.get(level.upper(), logging.INFO)

    root_logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    root_logger.setLevel(level)

    # Update all handlers
    for handler in root_logger.handlers:
        handler.setLevel(level)
