# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
"""
eTax Exception Hierarchy

Provides a consistent exception hierarchy for eTax operations.
All custom exceptions inherit from ETaxError for easy catching.
"""

from __future__ import annotations

from typing import Any


class ETaxError(Exception):
    """Base exception for all eTax errors.
    
    All eTax-specific exceptions should inherit from this class.
    This allows catching all eTax errors with a single except clause.
    
    Example:
        try:
            submit_declaration(data)
        except ETaxError as e:
            handle_etax_error(e)
    """
    
    def __init__(self, message: str, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details
        }


class ETaxAPIError(ETaxError):
    """Error from eTax API response.
    
    Raised when the eTax API returns an error response.
    
    Attributes:
        status_code: HTTP status code
        response_data: Raw response data from API
    """
    
    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        response_data: Any = None
    ):
        super().__init__(message, code)
        self.status_code = status_code
        self.response_data = response_data


class ETaxConnectionError(ETaxError):
    """Network/connection error to eTax API.
    
    Raised when unable to connect to the eTax API server.
    """
    pass


class ETaxAuthError(ETaxError):
    """Authentication error with eTax API.
    
    Raised when API credentials are invalid or token has expired.
    """
    pass


class ETaxValidationError(ETaxError):
    """Validation error for eTax data.
    
    Raised when input data fails validation before API call.
    
    Attributes:
        field: Field that failed validation
        errors: List of validation errors
    """
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        errors: list[str] | None = None
    ):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
        self.errors = errors or []


class ETaxDeclarationError(ETaxError):
    """Error during tax declaration operations.
    
    Raised when declaration submission or query fails.
    """
    pass


class ETaxConfigError(ETaxError):
    """Configuration error for eTax.
    
    Raised when required settings are missing or invalid.
    """
    pass


class ETaxTimeoutError(ETaxError):
    """Timeout error for eTax API call.
    
    Raised when API request exceeds timeout limit.
    """
    pass


class ETaxRateLimitError(ETaxError):
    """Rate limit exceeded for eTax API.
    
    Raised when too many requests are made in a short period.
    
    Attributes:
        retry_after: Seconds to wait before retrying
    """
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, code="RATE_LIMIT")
        self.retry_after = retry_after


class ETaxCertificateError(ETaxError):
    """Certificate error for eTax digital signatures.
    
    Raised when certificate operations fail.
    """
    pass


class ETaxSignatureError(ETaxError):
    """Digital signature error for eTax.
    
    Raised when signing or verification fails.
    """
    pass


# Export all exceptions
__all__ = [
    "ETaxError",
    "ETaxAPIError",
    "ETaxConnectionError",
    "ETaxAuthError",
    "ETaxValidationError",
    "ETaxDeclarationError",
    "ETaxConfigError",
    "ETaxTimeoutError",
    "ETaxRateLimitError",
    "ETaxCertificateError",
    "ETaxSignatureError",
]
