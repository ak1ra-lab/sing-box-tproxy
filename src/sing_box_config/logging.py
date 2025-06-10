# https://guicommits.com/how-to-log-in-python-like-a-pro/
# https://github.com/guilatrova/tryceratops/blob/main/src/tryceratops/logging_config.py
# https://docs.python.org/3/library/logging.config.html#logging-config-dictschema

import logging
import logging.config
import os
from pathlib import Path

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "brief": {
            "format": "%(message)s",
        },
        "precise": {
            "format": "[%(asctime)s][%(name)s][%(lineno)d][%(levelname)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "brief",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": [
            "console",
        ],
    },
}

logging_dir = Path(f"~/.local/state/{__package__}/log").expanduser()


def setup_logger(
    name: str, filename: str | None = None, debug: bool = os.environ.get("DEBUG", False)
) -> logging.Logger:
    """
    Sets up and configures a logger for the application.

    This function initializes a logger with the specified name and optional file-based logging.
    It uses a predefined logging configuration and supports both console and file handlers.
    If the `DEBUG` environment variable is set or `debug` is True, the logging level is set to DEBUG.

    Args:
        name (str): The name of the logger to create or retrieve.
        filename (str | None, optional): The name of the log file for file-based logging.
            If None, only console logging is used. Defaults to None.
        debug (bool, optional): Whether to enable debug-level logging.
            Defaults to the value of the `DEBUG` environment variable, or False if not set.

    Returns:
        logging.Logger: The configured logger instance.

    Notes:
        - This function should only be called once in the main entry point of the application.
        - Other modules should use `logging.getLogger(__name__)` to retrieve their logger.

    Raises:
        OSError: If the log directory cannot be created when file-based logging is enabled.
    """
    if debug:
        logging_config["root"]["level"] = "DEBUG"

    if not filename:
        logging.config.dictConfig(logging_config)
        return logging.getLogger(name)

    if not logging_dir.exists():
        logging_dir.mkdir(parents=True)

    logfile_handler = {
        "logfile": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": logging_dir / filename,
            "formatter": "precise",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
        }
    }

    logging_config["handlers"].update(logfile_handler)
    logging_config["root"]["handlers"].append("logfile")

    logging.config.dictConfig(logging_config)
    return logging.getLogger(name)
