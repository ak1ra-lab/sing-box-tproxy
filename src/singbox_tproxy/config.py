from pathlib import Path

log_dir = Path("~/.local/state/singbox_tproxy/log").expanduser()
log_file = log_dir / "messages.log"

# https://guicommits.com/how-to-log-in-python-like-a-pro/
# https://github.com/guilatrova/tryceratops/blob/main/src/tryceratops/logging_config.py
# https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
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
        "logfile": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "formatter": "precise",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": [
            "console",
            "logfile",
        ],
    },
}
