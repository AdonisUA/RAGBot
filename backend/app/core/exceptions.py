"""
Exception handlers for AI ChatBot
Custom exceptions and error handling
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog
from typing import Any, Dict

logger = structlog.get_logger()


class ChatBotException(Exception):
    """Base exception for ChatBot application"""

    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, status_code: int = 400):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class AIServiceException(ChatBotException):
    """Exception for AI service errors"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, status_code: int = 503):
        super().__init__(message, code, details, status_code)


class VoiceServiceException(ChatBotException):
    """Exception for voice service errors"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, status_code: int = 503):
        super().__init__(message, code, details, status_code)


class MemoryServiceException(ChatBotException):
    """Exception for memory service errors"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, status_code: int = 500):
        super().__init__(message, code, details, status_code)


class ValidationException(ChatBotException):
    """Exception for validation errors"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, status_code: int = 422):
        super().__init__(message, code, details, status_code)


class RateLimitException(ChatBotException):
    """Exception for rate limiting"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, status_code: int = 429):
        super().__init__(message, code, details, status_code)


class AuthenticationException(ChatBotException):
    """Exception for authentication errors"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, status_code: int = 401):
        super().__init__(message, code, details, status_code)


def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""

    @app.exception_handler(ChatBotException)
    async def chatbot_exception_handler(request: Request, exc: ChatBotException):
        """Handle custom ChatBot exceptions"""

        logger.error("ChatBot exception",
                    exception_type=type(exc).__name__,
                    message=exc.message,
                    code=exc.code,
                    details=exc.details,
                    path=request.url.path,
                    method=request.method)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": type(exc).__name__,
                "message": exc.message,
                "code": exc.code,
                "details": exc.details
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions (including FastAPI's HTTPException)"""

        logger.warning("HTTP exception",
                      status_code=exc.status_code,
                      detail=exc.detail,
                      path=request.url.path,
                      method=request.method)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""

        logger.warning("Validation error",
                      errors=exc.errors(),
                      path=request.url.path,
                      method=request.method)

        # Format validation errors for a more user-friendly response
        formatted_errors = []
        for error in exc.errors():
            loc = ".".join(map(str, error["loc"]))
            formatted_errors.append(f"{loc}: {error["msg"]}")

        return JSONResponse(
            status_code=422,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": formatted_errors
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""

        logger.error("Unhandled exception",
                    exception_type=type(exc).__name__,
                    error=str(exc),
                    path=request.url.path,
                    method=request.method,
                    exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "type": type(exc).__name__
            }
        )


def handle_ai_service_errors(func):
    """Decorator to handle AI service errors"""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error("AI service error",
                        function=func.__name__,
                        error=str(e))
            raise AIServiceException(
                message="AI service temporarily unavailable",
                code="AI_SERVICE_ERROR",
                details={"original_error": str(e)}
            )

    return wrapper


def handle_voice_service_errors(func):
    """Decorator to handle voice service errors"""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error("Voice service error",
                        function=func.__name__,
                        error=str(e))
            raise VoiceServiceException(
                message="Voice processing failed",
                code="VOICE_SERVICE_ERROR",
                details={"original_error": str(e)}
            )

    return wrapper


def handle_memory_service_errors(func):
    """Decorator to handle memory service errors"""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error("Memory service error",
                        function=func.__name__,
                        error=str(e))
            raise MemoryServiceException(
                message="Memory operation failed",
                code="MEMORY_SERVICE_ERROR",
                details={"original_error": str(e)}
            )

    return wrapper


class ErrorContext:
    """Context manager for error handling"""

    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context

    async def __aenter__(self):
        logger.debug("Operation started",
                    operation=self.operation,
                    **self.context)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error("Operation failed",
                        operation=self.operation,
                        exception_type=exc_type.__name__,
                        error=str(exc_val),
                        **self.context)
        else:
            logger.debug("Operation completed",
                        operation=self.operation,
                        **self.context)

        return False  # Don't suppress exceptions
