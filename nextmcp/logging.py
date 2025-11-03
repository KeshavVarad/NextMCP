"""
Centralized logging setup for NextMCP applications.

Provides consistent logging configuration across the framework and user applications.
"""

import logging
import sys
from pathlib import Path


# ANSI color codes for terminal output
class LogColors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels in terminal output.
    """

    LEVEL_COLORS = {
        logging.DEBUG: LogColors.GRAY,
        logging.INFO: LogColors.BLUE,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.MAGENTA,
    }

    def format(self, record):
        # Add color to level name
        if record.levelno in self.LEVEL_COLORS:
            record.levelname = (
                f"{self.LEVEL_COLORS[record.levelno]}{record.levelname}{LogColors.RESET}"
            )

        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    format_string: str | None = None,
    use_colors: bool = True,
) -> None:
    """
    Configure logging for NextMCP applications.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        format_string: Custom format string for log messages
        use_colors: Whether to use colored output in terminal (default: True)

    Example:
        from nextmcp.logging import setup_logging

        setup_logging(level="DEBUG", log_file="app.log")
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatters
    if use_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(format_string)
    else:
        console_formatter = logging.Formatter(format_string)

    file_formatter = logging.Formatter(format_string)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set logging level for nextmcp package
    logging.getLogger("nextmcp").setLevel(numeric_level)


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the logger (typically __name__)
        level: Optional logging level override

    Returns:
        Logger instance

    Example:
        from nextmcp.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
    """
    logger = logging.getLogger(name)

    if level:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)

    return logger


class LoggerContext:
    """
    Context manager for temporarily changing log level.

    Example:
        with LoggerContext("DEBUG"):
            # Debug logging is enabled here
            logger.debug("Detailed information")
        # Back to previous level
    """

    def __init__(self, level: str, logger: logging.Logger | None = None):
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.logger = logger or logging.getLogger()
        self.original_level = None

    def __enter__(self):
        self.original_level = self.logger.level
        self.logger.setLevel(self.level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.original_level)
        return False


def log_function_call(logger: logging.Logger = None):
    """
    Decorator to log function calls with parameters and return values.

    Args:
        logger: Optional logger instance (defaults to function's module logger)

    Example:
        @log_function_call()
        def my_function(x, y):
            return x + y
    """

    def decorator(fn):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(fn.__module__)

        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {fn.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = fn(*args, **kwargs)
                logger.debug(f"{fn.__name__} returned {result}")
                return result
            except Exception as e:
                logger.error(f"{fn.__name__} raised {type(e).__name__}: {e}")
                raise

        return wrapper

    return decorator


# Default logger for the nextmcp package
logger = get_logger("nextmcp")
