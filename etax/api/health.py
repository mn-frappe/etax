# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Health Check API for eTax

Provides endpoints for monitoring eTax app health and MTA connectivity.
"""

from datetime import datetime
from typing import Any

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def health():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Health status with timestamp
    """
    return {
        "status": "healthy",
        "app": "etax",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@frappe.whitelist()
def detailed_health():
    """
    Detailed health check with dependency status.
    
    Requires authentication. Checks:
    - Database connectivity
    - Redis/cache connectivity
    - eTax API settings
    - Digital certificate status
    - Pending reports status
    """
    frappe.only_for(["System Manager", "Administrator"])
    
    checks: dict[str, Any] = {
        "status": "healthy",
        "app": "etax",
        "version": get_app_version(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }
    
    # Database check
    checks["checks"]["database"] = check_database()
    
    # Cache check
    checks["checks"]["cache"] = check_cache()
    
    # Settings check
    checks["checks"]["settings"] = check_settings()
    
    # Certificate check
    checks["checks"]["certificate"] = check_certificate()
    
    # Pending reports
    checks["checks"]["pending_reports"] = check_pending_reports()
    
    # Circuit breaker status
    checks["checks"]["circuit_breaker"] = check_circuit_breaker()
    
    # Overall status
    critical_checks = ["database", "settings"]
    critical_healthy = all(
        checks["checks"].get(c, {}).get("status") == "healthy" 
        for c in critical_checks
    )
    all_healthy = all(
        c.get("status") in ["healthy", "disabled"] 
        for c in checks["checks"].values()
    )
    
    if not critical_healthy:
        checks["status"] = "unhealthy"
    elif not all_healthy:
        checks["status"] = "degraded"
    
    return checks


@frappe.whitelist()
def check_api_connectivity():
    """
    Test connectivity to MTA eTax API.
    
    Requires authentication.
    """
    frappe.only_for(["System Manager", "Administrator"])
    
    result = {
        "status": "unknown",
        "response_time_ms": None,
        "api_endpoint": None,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        import time
        
        settings = frappe.get_single("eTax Settings")
        if not getattr(settings, "enabled", False):
            result["status"] = "disabled"
            result["error"] = "eTax integration is disabled"
            return result
        
        result["api_endpoint"] = getattr(settings, "api_url", None)
        
        start_time = time.time()
        
        # Test connection
        from etax.api_client import ETaxClient
        client = ETaxClient()
        response = client.test_connection()
        
        end_time = time.time()
        result["response_time_ms"] = round((end_time - start_time) * 1000, 2)
        result["status"] = "healthy" if response else "unhealthy"
        
    except ImportError:
        result["status"] = "error"
        result["error"] = "eTax client not available"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


def get_app_version() -> str:
    """Get eTax app version"""
    try:
        return frappe.get_attr("etax.__version__")
    except AttributeError:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=frappe.get_app_path("etax"),
                capture_output=True,
                text=True
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"


def check_database() -> dict:
    """Check database connectivity"""
    try:
        frappe.db.sql("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_cache() -> dict:
    """Check Redis/cache connectivity"""
    try:
        test_key = "etax:health_check"
        frappe.cache().set_value(test_key, "ok", expires_in_sec=60)
        value = frappe.cache().get_value(test_key)
        if value == "ok":
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "Cache read/write mismatch"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_settings() -> dict:
    """Check eTax settings configuration"""
    try:
        settings = frappe.get_single("eTax Settings")
        
        issues = []
        if not getattr(settings, "enabled", False):
            return {"status": "disabled"}
        
        if not getattr(settings, "api_url", None):
            issues.append("API URL not configured")
        if not settings.get_password("api_key"):
            issues.append("API key not configured")
        
        if issues:
            return {"status": "warning", "issues": issues}
        
        return {"status": "healthy"}
    except frappe.DoesNotExistError:
        return {"status": "unhealthy", "error": "Settings not found"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_certificate() -> dict:
    """Check digital certificate status for MTA submissions"""
    try:
        settings = frappe.get_single("eTax Settings")
        
        if not getattr(settings, "enabled", False):
            return {"status": "disabled"}
        
        certificate_expiry = getattr(settings, "certificate_expiry", None)
        if not certificate_expiry:
            return {"status": "not_configured"}
        
        from frappe.utils import get_datetime
        expiry_dt = get_datetime(certificate_expiry)
        if expiry_dt is None:
            return {"status": "not_configured"}
        expiry = expiry_dt.date()
        today = datetime.now().date()
        days_remaining = (expiry - today).days
        
        if days_remaining < 0:
            return {
                "status": "unhealthy",
                "error": "Certificate expired",
                "expired_days_ago": abs(days_remaining)
            }
        elif days_remaining < 30:
            return {
                "status": "warning",
                "days_remaining": days_remaining,
                "expiry_date": str(expiry)
            }
        
        return {
            "status": "healthy",
            "days_remaining": days_remaining,
            "expiry_date": str(expiry)
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_pending_reports() -> dict:
    """Check pending tax reports status"""
    try:
        # Check for pending/failed reports
        pending_count = frappe.db.count(
            "eTax Report",
            {"status": ["in", ["Draft", "Pending", "Failed"]]}
        ) if frappe.db.table_exists("eTax Report") else 0
        
        # Check for overdue reports
        overdue_count = frappe.db.count(
            "eTax Report",
            {
                "status": "Draft",
                "due_date": ["<", datetime.now().date()]
            }
        ) if frappe.db.table_exists("eTax Report") else 0
        
        status = "healthy"
        if overdue_count > 0:
            status = "warning"
        
        return {
            "status": status,
            "pending_count": pending_count,
            "overdue_count": overdue_count
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_circuit_breaker() -> dict:
    """Check circuit breaker status"""
    try:
        from etax.utils.resilience import etax_circuit_breaker
        
        cb = etax_circuit_breaker
        return {
            "status": "healthy" if cb.state.value == "closed" else "degraded",
            "state": cb.state.value,
            "failure_count": getattr(cb, "failure_count", 0)
        }
    except ImportError:
        return {"status": "unknown", "error": "Resilience module not available"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@frappe.whitelist()
def readiness():
    """Kubernetes-style readiness probe"""
    try:
        frappe.db.sql("SELECT 1")
        
        settings = frappe.get_single("eTax Settings")
        if getattr(settings, "enabled", False) and not getattr(settings, "api_url", None):
            frappe.throw("Not ready: API URL not configured")
        
        return {"ready": True}
    except Exception as e:
        frappe.local.response.http_status_code = 503
        return {"ready": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def liveness():
    """Kubernetes-style liveness probe"""
    return {"alive": True, "timestamp": datetime.utcnow().isoformat() + "Z"}


@frappe.whitelist()
def tax_calendar_status():
    """
    Get upcoming tax deadlines status.
    
    Useful for monitoring tax compliance.
    """
    frappe.only_for(["System Manager", "Administrator", "Accountant"])
    
    today = datetime.now().date()
    
    deadlines = []
    
    # Common Mongolian tax deadlines
    tax_deadlines = [
        {"name": "VAT Monthly", "day": 25, "type": "monthly"},
        {"name": "PIT Monthly", "day": 10, "type": "monthly"},
        {"name": "CIT Quarterly", "day": 20, "type": "quarterly"},
        {"name": "Social Insurance", "day": 10, "type": "monthly"},
    ]
    
    for deadline in tax_deadlines:
        # Calculate next deadline
        next_date = today  # Initialize to avoid possibly unbound error
        if deadline["type"] == "monthly":
            next_date = today.replace(day=deadline["day"])
            if today.day > deadline["day"]:
                if today.month == 12:
                    next_date = next_date.replace(year=today.year + 1, month=1)
                else:
                    next_date = next_date.replace(month=today.month + 1)
        elif deadline["type"] == "quarterly":
            # Handle quarterly deadlines
            next_date = today.replace(day=deadline["day"])
        
        days_until = (next_date - today).days
        
        deadlines.append({
            "name": deadline["name"],
            "due_date": str(next_date),
            "days_until": days_until,
            "status": "urgent" if days_until <= 5 else "upcoming" if days_until <= 10 else "normal"
        })
    
    return {
        "deadlines": sorted(deadlines, key=lambda x: x["days_until"]),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
