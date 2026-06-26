"""Logging setup. Every operation logs to a rotating file under logs/.

Console output is intentionally quiet by default — frontends render their
own progress; the log file is the audit trail.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import ensure_dir, logs_dir

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger("harmonia")
    if _CONFIGURED:
        return logger

    logger.setLevel(logging.DEBUG)
    log_file = ensure_dir(logs_dir()) / "harmonia.log"
    handler = RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True
    return logger


def get_logger(name: str = "harmonia") -> logging.Logger:
    return logging.getLogger(name)
