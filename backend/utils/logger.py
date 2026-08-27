"""
logger.py
---------
Centralised, structured logging for the whole backend. Using one
configured logger instance keeps ingestion / retrieval / API logs
consistent and makes problems (e.g. a PDF that failed extraction)
easy to find instead of silently disappearing.
"""

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
