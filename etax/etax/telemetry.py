# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Telemetry - Anonymous Error Reporting to GitHub Issues

This module provides opt-in error reporting that creates GitHub issues
when critical errors occur. This helps the mn-frappe team improve eTax.

Privacy:
- No personal data is collected
- No credentials, TINs, or tax data is sent
- Only stack traces and environment info
- Users must explicitly enable this feature
"""

from __future__ import annotations

import hashlib
import traceback
from typing import TYPE_CHECKING

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.types import DF

# GitHub repository for issue creation
GITHUB_REPO = "mn-frappe/etax"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/issues"

# Rate limiting - max issues per day per site
MAX_ISSUES_PER_DAY = 5
CACHE_KEY = "etax_telemetry_issues_today"


def is_telemetry_enabled() -> bool:
    """Check if telemetry/error reporting is enabled in settings."""
    try:
        return bool(frappe.db.get_single_value("eTax Settings", "enable_error_reporting"))
    except Exception:
        return False


def get_github_token() -> str | None:
    """Get GitHub token for issue creation."""
    try:
        token = frappe.db.get_single_value("eTax Settings", "github_token")
        return str(token) if token else None
    except Exception:
        return None


def get_error_hash(error_message: str, stack_trace: str) -> str:
    """Generate a unique hash for an error to prevent duplicates."""
    content = f"{error_message}:{stack_trace[:500]}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def get_environment_info() -> dict:
    """Collect anonymous environment information."""
    info = {
        "frappe_version": getattr(frappe, "__version__", "unknown"),
        "etax_version": "unknown",
        "python_version": "unknown",
        "environment": "unknown",
    }

    try:
        from etax.hooks import app_version
        info["etax_version"] = app_version
    except Exception:
        try:
            info["etax_version"] = "1.3.0"
        except Exception:
            pass

    try:
        import sys
        info["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    except Exception:
        pass

    try:
        info["environment"] = frappe.db.get_single_value("eTax Settings", "environment") or "unknown"
    except Exception:
        pass

    return info


def check_rate_limit() -> bool:
    """Check if we've exceeded the daily rate limit."""
    count = frappe.cache.get_value(CACHE_KEY) or 0
    return count < MAX_ISSUES_PER_DAY


def increment_rate_limit():
    """Increment the daily issue count."""
    count = frappe.cache.get_value(CACHE_KEY) or 0
    # Cache expires at midnight (24 hours max)
    frappe.cache.set_value(CACHE_KEY, count + 1, expires_in_sec=86400)


def search_existing_issue(error_hash: str, token: str) -> str | None:
    """Search for existing issue with same error hash."""
    import requests

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    search_url = f"https://api.github.com/search/issues?q=repo:{GITHUB_REPO}+{error_hash}+in:body"

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("total_count", 0) > 0:
                return data["items"][0].get("html_url")
    except Exception:
        pass

    return None


def create_github_issue(
    title: str,
    body: str,
    labels: list[str] | None = None
) -> dict | None:
    """Create a GitHub issue for the error."""
    import requests

    token = get_github_token()
    if not token:
        frappe.log_error(
            "eTax Telemetry: GitHub token not configured",
            "Telemetry Configuration"
        )
        return None

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    data = {
        "title": title,
        "body": body,
        "labels": labels or ["bug", "auto-reported"],
    }

    try:
        response = requests.post(GITHUB_API_URL, json=data, headers=headers, timeout=10)
        if response.status_code == 201:
            return response.json()
        else:
            frappe.log_error(
                f"Failed to create GitHub issue: {response.status_code} - {response.text}",
                "eTax Telemetry"
            )
    except Exception as e:
        frappe.log_error(f"Failed to create GitHub issue: {e}", "eTax Telemetry")

    return None


def sanitize_data(data: dict) -> dict:
    """Remove sensitive data like TINs, credentials, tax amounts."""
    sensitive_keys = (
        'password', 'token', 'secret', 'key', 'api_key', 'access_token',
        'tin', 'taxpayer', 'regno', 'org_regno', 'ne_key', 'ent_id',
        'amount', 'tax', 'vat', 'refresh_token', 'username'
    )
    return {k: v for k, v in data.items()
            if not any(s in k.lower() for s in sensitive_keys)}


def format_issue_body(
    error_message: str,
    stack_trace: str,
    error_hash: str,
    context: dict | None = None
) -> str:
    """Format the GitHub issue body with error details."""
    env_info = get_environment_info()

    body = f"""## 🐛 Auto-Reported Error

**Error Hash:** `{error_hash}`

### Error Message
```
{error_message[:500]}
```

### Stack Trace
```python
{stack_trace[:2000]}
```

### Environment
| Property | Value |
|----------|-------|
| eTax Version | `{env_info['etax_version']}` |
| Frappe Version | `{env_info['frappe_version']}` |
| Python Version | `{env_info['python_version']}` |
| Environment | `{env_info['environment']}` |

"""

    if context:
        body += """### Context
```json
"""
        import json
        safe_context = sanitize_data(context)
        body += json.dumps(safe_context, indent=2, default=str)[:1000]
        body += """
```

"""

    body += """---
*This issue was automatically created by eTax Telemetry. The user has opted-in to anonymous error reporting.*
*No personal data, TINs, or tax information is included in this report.*
"""

    return body


def report_error(
    error_message: str,
    stack_trace: str | None = None,
    context: dict | None = None,
    severity: str = "error"
) -> dict | None:
    """
    Report an error to GitHub Issues.

    Args:
        error_message: The error message
        stack_trace: Optional stack trace (will capture current if not provided)
        context: Optional context dictionary (sensitive data will be filtered)
        severity: Error severity (error, warning, critical)

    Returns:
        GitHub issue response or None
    """
    # Check if telemetry is enabled
    if not is_telemetry_enabled():
        return None

    # Check rate limit
    if not check_rate_limit():
        frappe.log_error(
            "eTax Telemetry: Rate limit exceeded for today",
            "Telemetry Rate Limit"
        )
        return None

    # Get stack trace if not provided
    if not stack_trace:
        stack_trace = traceback.format_exc()

    # Generate error hash
    error_hash = get_error_hash(error_message, stack_trace)

    # Check for existing issue
    token = get_github_token()
    if token:
        existing = search_existing_issue(error_hash, token)
        if existing:
            frappe.log_error(
                f"eTax Telemetry: Similar issue already exists: {existing}",
                "Telemetry Duplicate"
            )
            return {"existing_issue": existing}

    # Format issue
    title = f"[Auto] {severity.upper()}: {error_message[:80]}"
    body = format_issue_body(error_message, stack_trace, error_hash, context)

    # Create issue
    result = create_github_issue(title, body, ["bug", "auto-reported", severity])

    if result:
        increment_rate_limit()
        frappe.log_error(
            f"eTax Telemetry: Created issue {result.get('html_url')}",
            "Telemetry Success"
        )

    return result


def handle_exception(e: Exception, context: dict | None = None):
    """
    Handle an exception and optionally report it.

    This can be used as a wrapper in try/except blocks:

    try:
        risky_operation()
    except Exception as e:
        handle_exception(e, {"operation": "risky_operation"})
        raise

    Args:
        e: The exception
        context: Optional context dictionary
    """
    error_message = str(e)
    stack_trace = traceback.format_exc()

    # Always log locally
    frappe.log_error(stack_trace, f"eTax Error: {error_message[:100]}")

    # Report to GitHub if enabled
    report_error(error_message, stack_trace, context)


# Frappe Error Hook
def on_error(error: str):
    """
    Frappe error hook - called on unhandled exceptions.

    This is registered in hooks.py as:
    exception_handler = "etax.etax.telemetry.on_error"
    """
    if not is_telemetry_enabled():
        return

    try:
        stack_trace = traceback.format_exc()
        report_error(error, stack_trace, severity="critical")
    except Exception:
        # Don't let telemetry errors break the app
        pass


# Utility to test telemetry
@frappe.whitelist()
def test_telemetry():
    """Test the telemetry system (creates a test issue if configured)."""
    frappe.only_for("System Manager")

    if not is_telemetry_enabled():
        return {"status": "error", "message": _("Error reporting is not enabled in eTax Settings")}

    if not get_github_token():
        return {"status": "error", "message": _("GitHub token is not configured")}

    # Don't actually create test issues in production
    return {
        "status": "ok",
        "message": _("Telemetry is configured correctly"),
        "github_repo": GITHUB_REPO,
        "rate_limit_remaining": MAX_ISSUES_PER_DAY - (frappe.cache.get_value(CACHE_KEY) or 0)
    }
