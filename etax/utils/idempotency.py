# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Idempotency Utilities for eTax

Prevents duplicate tax report submissions. Critical for eTax where
duplicate submissions can cause compliance issues with MTA.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, TypeVar, cast

import frappe
from frappe import _

T = TypeVar("T")


@dataclass
class IdempotencyResult:
    """Result of an idempotent operation"""
    is_duplicate: bool
    cached_result: Any | None = None
    idempotency_key: str | None = None
    original_timestamp: datetime | None = None


class IdempotencyManager:
    """
    Manages idempotency for eTax operations.
    
    Prevents duplicate tax report submissions.
    """
    
    def __init__(self, app_name: str = "etax"):
        self.app_name = app_name
        self.cache_prefix = f"idempotency:{app_name}"
    
    def generate_key(self, operation: str, **params) -> str:
        """Generate idempotency key from operation and parameters"""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_source = f"{operation}:{sorted_params}"
        key_hash = hashlib.sha256(key_source.encode()).hexdigest()[:16]
        return f"{self.cache_prefix}:{operation}:{key_hash}"
    
    def check(self, key: str) -> IdempotencyResult:
        """Check if operation was already processed"""
        cached = frappe.cache().get_value(key)
        
        if cached:
            return IdempotencyResult(
                is_duplicate=True,
                cached_result=cached.get("result"),
                idempotency_key=key,
                original_timestamp=datetime.fromisoformat(cached["timestamp"]) if cached.get("timestamp") else None
            )
        
        return IdempotencyResult(
            is_duplicate=False,
            idempotency_key=key
        )
    
    def store(self, key: str, result: Any, ttl_hours: int = 24):
        """Store operation result for idempotency checking"""
        data = {
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "app": self.app_name
        }
        
        frappe.cache().set_value(
            key,
            data,
            expires_in_sec=ttl_hours * 3600
        )
    
    def invalidate(self, key: str):
        """Remove idempotency key"""
        frappe.cache().delete_value(key)
    
    def get_or_execute(
        self,
        operation: str,
        func: Callable[..., T],
        ttl_hours: int = 24,
        **params
    ) -> tuple[T, bool]:
        """Execute function only if not already processed"""
        key = self.generate_key(operation, **params)
        check_result = self.check(key)
        
        if check_result.is_duplicate:
            frappe.logger(self.app_name).info(
                f"Idempotency hit for {operation}"
            )
            return cast(T, check_result.cached_result), True
        
        result = func(**params)
        self.store(key, result, ttl_hours)
        
        return result, False


# Singleton instance
idempotency = IdempotencyManager("etax")


def idempotent(operation: str, ttl_hours: int = 24, key_params: list[str] | None = None):
    """Decorator to make a function idempotent"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            if key_params:
                params = {k: v for k, v in bound.arguments.items() if k in key_params}
            else:
                params = dict(bound.arguments)
            
            key = idempotency.generate_key(operation, **params)
            check_result = idempotency.check(key)
            
            if check_result.is_duplicate:
                frappe.logger("etax").info(
                    f"Idempotent operation '{operation}' already processed"
                )
                return cast(T, check_result.cached_result)
            
            result = func(*args, **kwargs)
            idempotency.store(key, result, ttl_hours)
            
            return result
        
        return wrapper
    return decorator


# eTax-specific idempotency helpers

def get_report_submission_key(
    ent_id: str,
    tax_type_code: str,
    year: int,
    period: int,
    form_no: str | None = None
) -> str:
    """
    Generate idempotency key for tax report submission.
    
    Key is based on entity, tax type, period - not document modified time,
    because MTA tracks by these fields, not our internal IDs.
    """
    return idempotency.generate_key(
        "submit_report",
        ent_id=ent_id,
        tax_type_code=tax_type_code,
        year=year,
        period=period,
        form_no=form_no or "default"
    )


def check_report_submission(
    ent_id: str,
    tax_type_code: str,
    year: int,
    period: int,
    form_no: str | None = None
) -> IdempotencyResult:
    """Check if tax report was already submitted for this period"""
    key = get_report_submission_key(ent_id, tax_type_code, year, period, form_no)
    return idempotency.check(key)


def store_report_submission_result(
    ent_id: str,
    tax_type_code: str,
    year: int,
    period: int,
    result: dict,
    form_no: str | None = None
):
    """Store successful report submission result"""
    key = get_report_submission_key(ent_id, tax_type_code, year, period, form_no)
    # Store for period duration + buffer (monthly = 45 days, annual = 400 days)
    ttl_hours = 400 * 24 if period in [0, 1] else 45 * 24
    idempotency.store(key, result, ttl_hours)


def invalidate_report_submission(
    ent_id: str,
    tax_type_code: str,
    year: int,
    period: int,
    form_no: str | None = None
):
    """
    Invalidate idempotency for a report.
    
    Call this when report needs to be resubmitted (e.g., returned by MTA).
    """
    key = get_report_submission_key(ent_id, tax_type_code, year, period, form_no)
    idempotency.invalidate(key)


# Draft save idempotency (less strict, shorter TTL)

def check_draft_save(report_name: str) -> IdempotencyResult:
    """Check if draft was recently saved (prevent rapid duplicate saves)"""
    key = idempotency.generate_key("save_draft", report_name=report_name)
    return idempotency.check(key)


def store_draft_save(report_name: str, result: dict):
    """Store draft save result (short TTL to allow re-save)"""
    key = idempotency.generate_key("save_draft", report_name=report_name)
    idempotency.store(key, result, ttl_hours=1)  # 1 hour cooldown
