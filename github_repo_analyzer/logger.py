"""
Structured logging configuration for GitHub Repo Analyzer.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional


def get_logger(name: str, log_level: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file for file logging

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Determine log level
    level_str = log_level or os.environ.get('GITHUB_ANALYZER_LOG_LEVEL', 'INFO').upper()
    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    log_file_path = log_file or os.environ.get('GITHUB_ANALYZER_LOG_FILE')
    if log_file_path:
        try:
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Failed to set up file logging to {log_file_path}: {e}")

    return logger
