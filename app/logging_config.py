"""Centralized logging setup, called once at app startup.

Two distinct loggers, kept separate on purpose:

- "app"   — technical/runtime log: startup, requests, exceptions, warnings.
  Written to logs/app.log (rotating) and echoed to the console, since this
  is what you want to watch while developing/running the server.

- "audit" — a record of what happened to the *data*: an upload was
  received, a row was rejected by the dedup/continuity check, an
  categorization run resolved/flagged N rows, a migration moved N rows for
  account X into afschrift. Written to logs/audit.log (rotating) only —
  this is a durable trail for an accounting app, not a debugging stream,
  so it deliberately stays out of the console.

Use get_app_logger()/get_audit_logger() (or plain
logging.getLogger("app"/"audit")) anywhere in the codebase — don't
configure handlers more than once.
"""
import logging
from logging.handlers import RotatingFileHandler

from app.config import LOG_DIR

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # -- "app": technical/runtime log -----------------------------------
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)

    app_file_handler = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    app_file_handler.setFormatter(fmt)
    app_logger.addHandler(app_file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    app_logger.addHandler(console_handler)

    # -- "audit": data-change trail --------------------------------------
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)

    audit_file_handler = RotatingFileHandler(
        LOG_DIR / "audit.log", maxBytes=2_000_000, backupCount=10, encoding="utf-8"
    )
    audit_file_handler.setFormatter(fmt)
    audit_logger.addHandler(audit_file_handler)

    _CONFIGURED = True


def get_app_logger() -> logging.Logger:
    return logging.getLogger("app")


def get_audit_logger() -> logging.Logger:
    return logging.getLogger("audit")
