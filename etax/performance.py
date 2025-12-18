# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
eTax Performance Utilities

Provides VAT data caching, pre-aggregation, and performance optimizations
for tax reporting operations.
"""

import functools
import time
from typing import Any

import frappe
from frappe.utils import flt, get_first_day, get_last_day, getdate

# Import logger utilities
from etax.logger import (
    log_debug,
    log_error,
    log_info,
    log_scheduler_task,
)

# =============================================================================
# Performance Indexes
# =============================================================================

ETAX_INDEXES = [
    # Taxpayer lookup
    {
        "table": "tabeTax Taxpayer",
        "columns": ["tin"],
        "name": "idx_etax_taxpayer_tin"
    },
    # Report period tracking
    {
        "table": "tabeTax Report Period",
        "columns": ["company", "period", "status"],
        "name": "idx_etax_period"
    },
    # VAT Sales cache
    {
        "table": "tabeTax Sales Invoice Cache",
        "columns": ["company", "period"],
        "name": "idx_etax_sales_cache"
    },
    # VAT Purchases cache
    {
        "table": "tabeTax Purchase Invoice Cache",
        "columns": ["company", "period"],
        "name": "idx_etax_purchase_cache"
    },
]


def ensure_indexes():
    """Create performance indexes if they don't exist."""
    for idx in ETAX_INDEXES:
        try:
            index_name = idx["name"]
            table = idx["table"]
            columns = ", ".join([f"`{c}`" for c in idx["columns"]])

            # Check if index exists
            existing = frappe.db.sql(f"""
                SHOW INDEX FROM `{table}` WHERE Key_name = %s
            """, (index_name,))

            if not existing:
                frappe.db.sql(f"""
                    CREATE INDEX `{index_name}` ON `{table}` ({columns})
                """)
                frappe.logger("etax").info(f"Created index {index_name} on {table}")
        except Exception as e:
            frappe.logger("etax").debug(f"Could not create index {idx['name']}: {e}")


# =============================================================================
# Caching Utilities
# =============================================================================

def cache_key(prefix: str, *args) -> str:
    """Generate a cache key."""
    return f"etax:{prefix}:" + ":".join(str(a) for a in args)


def get_cached(key: str):
    """Get value from cache."""
    return frappe.cache().get_value(key)


def set_cached(key: str, value: Any, ttl: int = 3600):
    """Set value in cache with TTL."""
    frappe.cache().set_value(key, value, expires_in_sec=ttl)


def invalidate_cache(pattern: str):
    """Invalidate cache keys matching pattern."""
    frappe.cache().delete_keys(f"etax:{pattern}*")


# =============================================================================
# TIN Lookup Caching
# =============================================================================

def get_taxpayer_info_cached(tin: str, validate: bool = False) -> dict | None:
    """
    Get taxpayer info from cache or API.

    Args:
        tin: Taxpayer Identification Number
        validate: If True, validates with eTax API

    Returns:
        Taxpayer information dict or None
    """
    if not tin:
        return None

    # Clean TIN
    tin = str(tin).strip().replace(" ", "")

    key = cache_key("taxpayer", tin)
    cached = get_cached(key)

    if cached and not validate:
        return cached

    # Check local database first
    local = frappe.get_value(
        "eTax Taxpayer",
        {"tin": tin},
        ["name", "tin", "company_name", "company_name_en", "address"],
        as_dict=True
    )

    if local:
        if isinstance(local, dict):
            set_cached(key, local, ttl=86400)  # Cache for 24 hours
            return local
        return None

    # Validate with API if requested
    if validate:
        try:
            from etax.api.client import ETaxClient
            client = ETaxClient()
            api_data = client.get_taxpayer_info(tin) if hasattr(client, "get_taxpayer_info") else None

            if api_data:
                # Save locally
                taxpayer = frappe.new_doc("eTax Taxpayer")
                taxpayer.tin = tin
                taxpayer.company_name = api_data.get("company_name", "")
                taxpayer.company_name_en = api_data.get("company_name_en", "")
                taxpayer.address = api_data.get("address", "")
                taxpayer.flags.ignore_permissions = True
                taxpayer.save()

                set_cached(key, api_data, ttl=86400)
                return api_data
        except Exception as e:
            frappe.logger("etax").warning(f"Failed to validate TIN {tin}: {e}")

    return None


def batch_validate_tins(tins: list[str]) -> dict[str, dict]:
    """
    Batch validate TINs for better performance.

    Args:
        tins: List of TINs to validate

    Returns:
        Dict mapping TIN to taxpayer info
    """
    results = {}
    to_validate = []

    # Check cache first
    for tin in tins:
        if not tin:
            continue
        tin = str(tin).strip()
        cached = get_taxpayer_info_cached(tin)
        if cached:
            results[tin] = cached
        else:
            to_validate.append(tin)

    # Batch validate remaining
    if to_validate:
        # Use background job for large batches
        if len(to_validate) > 10:
            frappe.enqueue(
                "_batch_validate_tins_worker",
                tins=to_validate,
                queue="short"
            )
            for tin in to_validate:
                results[tin] = {"tin": tin, "status": "pending_validation"}
        else:
            for tin in to_validate:
                info = get_taxpayer_info_cached(tin, validate=True)
                results[tin] = info or {"tin": tin, "status": "not_found"}

    return results


def _batch_validate_tins_worker(tins: list[str]):
    """Background worker for batch TIN validation."""
    for tin in tins:
        try:
            get_taxpayer_info_cached(tin, validate=True)
        except Exception as e:
            frappe.logger("etax").warning(f"Batch TIN validation failed for {tin}: {e}")


# =============================================================================
# VAT Data Pre-aggregation
# =============================================================================

def get_vat_sales_summary_cached(
    company: str,
    period: str,
    force_refresh: bool = False
) -> dict:
    """
    Get VAT sales summary from cache or calculate.

    Args:
        company: Company name
        period: Period string (e.g., "2024-01")
        force_refresh: Force recalculation

    Returns:
        VAT sales summary dict
    """
    key = cache_key("vat_sales", company, period)

    if not force_refresh:
        cached = get_cached(key)
        if cached:
            return cached

    # Calculate from Sales Invoices
    result = calculate_vat_sales_summary(company, period)
    set_cached(key, result, ttl=3600)

    return result


def calculate_vat_sales_summary(company: str, period: str) -> dict:
    """
    Calculate VAT sales summary for a period.

    Args:
        company: Company name
        period: Period string (e.g., "2024-01")
    """
    year, month = map(int, period.split("-"))
    month_start = get_first_day(f"{year}-{month:02d}-01")
    month_end = get_last_day(month_start)

    # Get all sales invoices for the period
    inv_result = list(frappe.db.sql("""
        SELECT
            COUNT(*) as count,
            COALESCE(SUM(base_net_total), 0) as net_total,
            COALESCE(SUM(total_taxes_and_charges), 0) as vat_amount,
            COALESCE(SUM(base_grand_total), 0) as grand_total
        FROM `tabSales Invoice`
        WHERE company = %s
        AND posting_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, month_start, month_end), as_dict=True))
    invoices = inv_result[0] if inv_result else {"count": 0, "net_total": 0, "vat_amount": 0, "grand_total": 0}

    # Get by customer type (domestic vs export)
    dom_result = list(frappe.db.sql("""
        SELECT
            COUNT(*) as count,
            COALESCE(SUM(base_net_total), 0) as net_total,
            COALESCE(SUM(total_taxes_and_charges), 0) as vat_amount,
            COALESCE(SUM(base_grand_total), 0) as grand_total
        FROM `tabSales Invoice`
        WHERE company = %s
        AND posting_date BETWEEN %s AND %s
        AND docstatus = 1
        AND COALESCE(is_internal_customer, 0) = 0
        AND COALESCE(territory, '') NOT IN ('Foreign', 'Export', 'International')
    """, (company, month_start, month_end), as_dict=True))
    domestic = dom_result[0] if dom_result else {"count": 0, "net_total": 0, "vat_amount": 0, "grand_total": 0}

    inv_count = int(invoices.get("count", 0) or 0)
    dom_count = int(domestic.get("count", 0) or 0)
    inv_net = flt(invoices.get("net_total", 0))
    dom_net = flt(domestic.get("net_total", 0))
    inv_vat = flt(invoices.get("vat_amount", 0))
    dom_vat = flt(domestic.get("vat_amount", 0))
    inv_grand = flt(invoices.get("grand_total", 0))
    dom_grand = flt(domestic.get("grand_total", 0))

    return {
        "company": company,
        "period": period,
        "total": {
            "count": inv_count,
            "net_total": inv_net,
            "vat_amount": inv_vat,
            "grand_total": inv_grand
        },
        "domestic": {
            "count": dom_count,
            "net_total": dom_net,
            "vat_amount": dom_vat,
            "grand_total": dom_grand
        },
        "export": {
            "count": inv_count - dom_count,
            "net_total": inv_net - dom_net,
            "vat_amount": inv_vat - dom_vat,
            "grand_total": inv_grand - dom_grand
        }
    }


def get_vat_purchase_summary_cached(
    company: str,
    period: str,
    force_refresh: bool = False
) -> dict:
    """
    Get VAT purchase summary from cache or calculate.
    """
    key = cache_key("vat_purchase", company, period)

    if not force_refresh:
        cached = get_cached(key)
        if cached:
            return cached

    result = calculate_vat_purchase_summary(company, period)
    set_cached(key, result, ttl=3600)

    return result


def calculate_vat_purchase_summary(company: str, period: str) -> dict:
    """
    Calculate VAT purchase summary for a period.
    """
    year, month = map(int, period.split("-"))
    month_start = get_first_day(f"{year}-{month:02d}-01")
    month_end = get_last_day(month_start)

    inv_result = list(frappe.db.sql("""
        SELECT
            COUNT(*) as count,
            COALESCE(SUM(base_net_total), 0) as net_total,
            COALESCE(SUM(total_taxes_and_charges), 0) as vat_amount,
            COALESCE(SUM(base_grand_total), 0) as grand_total
        FROM `tabPurchase Invoice`
        WHERE company = %s
        AND posting_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, month_start, month_end), as_dict=True))
    invoices = inv_result[0] if inv_result else {"count": 0, "net_total": 0, "vat_amount": 0, "grand_total": 0}

    return {
        "company": company,
        "period": period,
        "total": {
            "count": int(invoices.get("count", 0) or 0),
            "net_total": flt(invoices.get("net_total", 0)),
            "vat_amount": flt(invoices.get("vat_amount", 0)),
            "grand_total": flt(invoices.get("grand_total", 0))
        }
    }


# =============================================================================
# Auto-Sync Tax Reports (Autopilot)
# =============================================================================

def auto_sync_tax_reports():
    """
    Automatically sync tax reports from eTax API.
    Called by scheduler based on autopilot settings.
    """
    settings = frappe.get_single("eTax Settings")
    if not getattr(settings, "auto_sync_reports", False):
        return

    try:
        from etax.api.client import ETaxClient
        client = ETaxClient()

        # Fetch report periods from API
        periods = client.get_report_periods() if hasattr(client, "get_report_periods") else []

        for period in periods:
            frappe.enqueue(
                "etax.setup.sync.sync_report_period",
                period_data=period,
                queue="short"
            )

    except Exception as e:
        frappe.log_error(f"Auto-sync tax reports failed: {e}")


# NOTE: Auto-submit functionality has been removed.
# Tax reports now require manual approval workflow before submission.
# See: eTax Report Approval workflow (Tax Report Preparer → Reviewer → Approver)


# =============================================================================
# Invoice Hook for Cache Invalidation
# =============================================================================

def on_invoice_update(doc, method=None):
    """
    Invalidate cache when Sales/Purchase Invoice is submitted/cancelled.
    """
    if not doc.company or not doc.posting_date:
        return

    posting_date = getdate(doc.posting_date)
    if not posting_date:
        return

    period = f"{posting_date.year}-{posting_date.month:02d}"

    # Determine invoice type
    if doc.doctype == "Sales Invoice":
        key = cache_key("vat_sales", doc.company, period)
    else:
        key = cache_key("vat_purchase", doc.company, period)

    frappe.cache().delete_value(key)


# =============================================================================
# Performance Monitoring
# =============================================================================

def track_api_performance(method: str):
    """Decorator to track API call performance."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            success = True
            try:
                return func(*args, **kwargs)
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start
                try:
                    frappe.cache().hincrby("etax:api_stats", f"{method}:calls", 1)
                    frappe.cache().hincrbyfloat("etax:api_stats", f"{method}:time", duration)
                    if not success:
                        frappe.cache().hincrby("etax:api_stats", f"{method}:errors", 1)
                except Exception:
                    pass
        return wrapper
    return decorator


def get_api_stats() -> dict:
    """Get API performance statistics."""
    stats = frappe.cache().hgetall("etax:api_stats") or {}
    return stats


def clear_api_stats():
    """Clear API performance statistics."""
    frappe.cache().delete_value("etax:api_stats")
