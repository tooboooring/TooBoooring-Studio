"""
Logging utility for Video Production App.

This module provides a centralized logging system that replaces print() statements
throughout the application. It supports both console and file logging with
configurable log levels.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Path to log file (None to disable file logging)
        level: Overall logger level
        console_level: Console handler level
        file_level: File handler level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (for production/debugging)
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler to prevent huge log files
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(file_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # If we can't create log file, just log to console
            logger.warning(f"Could not create log file {log_file}: {e}")
    
    return logger


# Create default logger for the application
_log_dir = Path(__file__).parent.parent.parent / "logs"
_default_log_file = _log_dir / "app.log"
app_logger = setup_logger(
    "video_production_app",
    log_file=_default_log_file,
    level=logging.DEBUG,
    console_level=logging.INFO,
    file_level=logging.DEBUG
)

