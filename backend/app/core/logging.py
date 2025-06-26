"""
Logging configuration for AI ChatBot
Structured logging with JSON format
"""

import logging
import logging.handlers
import sys
from pathlib import Path
import structlog
from typing import Any, Dict

from app.core.config import get_settings


def setup_logging(log_level: str = "INFO"):
    """Setup structured logging configuration"""

    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )

    # Setup file logging if enabled
    if settings.log_file_enabled:
        setup_file_logging(settings)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json"
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def setup_file_logging(settings):
    """Setup file logging with rotation"""

    # Create logs directory
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse max file size
    max_bytes = parse_file_size(settings.log_file_max_size)

    # Setup rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=settings.log_file_path,
        maxBytes=max_bytes,
        backupCount=settings.log_file_backup_count,
        encoding='utf-8'
    )

    # Set formatter
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    file_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)


def parse_file_size(size_str: str) -> int:
    """Parse file size string to bytes"""

    size_str = size_str.upper()

    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


class JSONFormatter(logging.Formatter):
    """JSON log formatter"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""

        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, 'pathname'):
            log_entry["file"] = record.pathname
            log_entry["line"] = record.lineno

        if hasattr(record, 'funcName'):
            log_entry["function"] = record.funcName

        # Add exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add custom fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno',
                          'pathname', 'filename', 'module', 'lineno',
                          'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process',
                          'exc_info', 'exc_text', 'stack_info', 'getMessage']:
                log_entry[key] = value

        return structlog.processors.JSONRenderer()(None, None, log_entry)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get structured logger instance"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging to any class"""

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class"""
        return structlog.get_logger(self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls"""

    def wrapper(*args, **kwargs):
        logger = structlog.get_logger(func.__module__)

        logger.debug("Function called",
                    function=func.__name__,
                    args=len(args),
                    kwargs=list(kwargs.keys()))

        try:
            result = func(*args, **kwargs)
            logger.debug("Function completed",
                        function=func.__name__)
            return result
        except Exception as e:
            logger.error("Function failed",
                        function=func.__name__,
                        error=str(e))
            raise

    return wrapper


async def log_async_function_call(func):
    """Decorator to log async function calls"""

    async def wrapper(*args, **kwargs):
        logger = structlog.get_logger(func.__module__)

        logger.debug("Async function called",
                    function=func.__name__,
                    args=len(args),
                    kwargs=list(kwargs.keys()))

        try:
            result = await func(*args, **kwargs)
            logger.debug("Async function completed",
                        function=func.__name__)
            return result
        except Exception as e:
            logger.error("Async function failed",
                        function=func.__name__,
                        error=str(e))
            raise

    return wrapper


def setup_uvicorn_logging():
    """Setup logging for Uvicorn server"""

    # Configure uvicorn loggers
    uvicorn_loggers = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access"
    ]

    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True


def setup_third_party_logging():
    """Setup logging for third-party libraries"""

    # Reduce noise from third-party libraries
    noisy_loggers = [
        "httpx",
        "httpcore",
        "openai",
        "urllib3",
        "asyncio"
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
