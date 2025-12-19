# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Resilient HTTP Client Wrapper for eTax

Wraps the existing HTTP client with:
- Circuit breaker integration
- Structured logging with correlation IDs
- Metrics collection
- Certificate validation checks
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe

from etax.api.http_client import ETaxHTTPClient, ETaxHTTPError


class ResilientETaxClient:
    """
    Resilient wrapper for ETaxHTTPClient.
    
    Adds:
    - Circuit breaker for fault tolerance
    - Structured logging with correlation IDs
    - Metrics collection for monitoring
    - Certificate expiry warnings
    
    Usage:
        client = ResilientETaxClient()
        
        # Simple usage
        result = client.get("/api/beta/forms")
        
        # With correlation ID for tracing
        with client.traced("submit_report") as ctx:
            result = ctx.post("/api/beta/submitform", data=report_data)
    """
    
    def __init__(self, settings=None):
        self._inner_client = ETaxHTTPClient(settings)
        self._circuit_breaker = None
        self._logger = None
        self._metrics = None
    
    @property
    def circuit_breaker(self):
        """Lazy load circuit breaker"""
        if self._circuit_breaker is None:
            try:
                from etax.utils.resilience import etax_circuit_breaker
                self._circuit_breaker = etax_circuit_breaker
            except ImportError:
                self._circuit_breaker = None
        return self._circuit_breaker
    
    @property
    def logger(self):
        """Lazy load structured logger"""
        if self._logger is None:
            try:
                from etax.utils.logging import get_logger
                self._logger = get_logger()
            except ImportError:
                self._logger = None
        return self._logger
    
    @property
    def metrics(self):
        """Lazy load metrics collector"""
        if self._metrics is None:
            try:
                from etax.utils.metrics import metrics
                self._metrics = metrics
            except ImportError:
                self._metrics = None
        return self._metrics
    
    def _check_certificate_expiry(self):
        """Check if certificate is expiring soon"""
        try:
            from datetime import date, timedelta
            settings = self._inner_client.settings
            cert_expiry = getattr(settings, "certificate_expiry", None) if settings else None
            if cert_expiry:
                expiry = cert_expiry
                if isinstance(expiry, str):
                    expiry = date.fromisoformat(expiry)
                
                days_remaining = (expiry - date.today()).days
                if days_remaining <= 30:
                    if self.logger:
                        self.logger.warning(
                            f"eTax certificate expires in {days_remaining} days",
                            extra={"days_remaining": days_remaining}
                        )
                    if self.metrics:
                        self.metrics.gauge("etax_certificate_days_remaining", days_remaining)
        except Exception:
            pass
    
    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for metrics"""
        if isinstance(error, ETaxHTTPError):
            status = error.status_code or 0
            if status == 408:
                return "timeout"
            elif status == 429:
                return "rate_limited"
            elif status == 503:
                return "service_unavailable"
            elif status == 401:
                return "auth_error"
            elif status == 201:
                return "retry_requested"
            elif status >= 500:
                return "server_error"
            elif status >= 400:
                return "client_error"
        
        error_str = str(error).lower()
        if "certificate" in error_str:
            return "certificate_error"
        elif "signature" in error_str:
            return "signature_error"
        
        return "unknown"
    
    def _execute_with_resilience(self, operation: str, func, *args, **kwargs) -> Any:
        """Execute function with circuit breaker and metrics"""
        
        # Check certificate on first call
        self._check_certificate_expiry()
        
        # Log request
        if self.logger:
            self.logger.info(
                f"eTax API call: {operation}",
                extra={"operation": operation, "endpoint": args[0] if args else None}
            )
        
        error_type = None
        
        try:
            # Execute with circuit breaker if available
            if self.circuit_breaker:
                result = self.circuit_breaker.call(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success metrics
            if self.metrics:
                self.metrics.increment("etax_api_requests", tags={"operation": operation, "status": "success"})
            
            return result
            
        except Exception as e:
            error_type = self._categorize_error(e)
            
            # Log error
            if self.logger:
                self.logger.error(
                    f"eTax API error: {operation}",
                    extra={"operation": operation, "error_type": error_type, "error": str(e)}
                )
            
            # Record error metrics
            if self.metrics:
                self.metrics.increment("etax_api_requests", tags={"operation": operation, "status": "error"})
                self.metrics.increment("etax_api_errors", tags={"operation": operation, "error_type": error_type})
            
            raise
    
    @contextmanager
    def traced(self, operation: str):
        """
        Context manager for traced API calls.
        
        Usage:
            with client.traced("submit_report") as ctx:
                result = ctx.post("/api/beta/submitform", data=report)
        """
        import time
        import uuid
        
        correlation_id = str(uuid.uuid4())[:8]
        if hasattr(frappe, "local"):
            frappe.local.correlation_id = correlation_id
        
        start_time = time.time()
        
        try:
            yield self
        finally:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.timing(f"etax_api_duration_{operation}", duration)
            
            if hasattr(frappe, "local") and hasattr(frappe.local, "correlation_id"):
                delattr(frappe.local, "correlation_id")
    
    def get(self, endpoint: str, auth_header=None, headers=None, params=None) -> Any:
        """Make GET request with resilience"""
        return self._execute_with_resilience(
            "get",
            self._inner_client.get,
            endpoint,
            auth_header=auth_header,
            headers=headers,
            params=params
        )
    
    def post(self, endpoint: str, data=None, auth_header=None, headers=None, params=None) -> Any:
        """Make POST request with resilience"""
        return self._execute_with_resilience(
            "post",
            self._inner_client.post,
            endpoint,
            data=data,
            auth_header=auth_header,
            headers=headers,
            params=params
        )
    
    # Expose inner client properties
    @property
    def base_url(self):
        return self._inner_client.base_url
    
    @property
    def settings(self):
        return self._inner_client.settings
    
    @property
    def environment(self):
        return self._inner_client.environment


def get_resilient_client(settings=None) -> ResilientETaxClient:
    """Get resilient eTax HTTP client"""
    return ResilientETaxClient(settings)


def resilient_request(method: str, endpoint: str, **kwargs) -> Any:
    """Make a resilient API request"""
    client = get_resilient_client()
    if method.upper() == "GET":
        return client.get(endpoint, **kwargs)
    elif method.upper() == "POST":
        return client.post(endpoint, **kwargs)
    else:
        raise ValueError(f"Unsupported method: {method}")
