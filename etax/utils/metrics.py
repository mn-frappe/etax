# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Metrics and Telemetry for eTax

Collects operational metrics for monitoring tax operations.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import frappe


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: dict = field(default_factory=dict)


class MetricsCollector:
    """Collects and stores metrics for eTax operations"""
    
    CACHE_PREFIX = "metrics:etax"
    DEFAULT_TTL = 86400
    
    def increment(self, name: str, value: float = 1, tags: dict | None = None):
        key = self._make_key(name, tags)
        try:
            current = frappe.cache().get_value(key) or 0
            frappe.cache().set_value(key, current + value, expires_in_sec=self.DEFAULT_TTL)
        except Exception:
            pass
    
    def gauge(self, name: str, value: float, tags: dict | None = None):
        key = self._make_key(name, tags)
        data = {"value": value, "timestamp": datetime.utcnow().isoformat()}
        try:
            frappe.cache().set_value(key, data, expires_in_sec=self.DEFAULT_TTL)
        except Exception:
            pass
    
    def timing(self, name: str, duration_ms: float, tags: dict | None = None):
        key = self._make_key(f"{name}:timings", tags)
        try:
            timings = frappe.cache().get_value(key) or []
            timings.append({"value": duration_ms, "timestamp": datetime.utcnow().isoformat()})
            timings = timings[-100:]
            frappe.cache().set_value(key, timings, expires_in_sec=self.DEFAULT_TTL)
        except Exception:
            pass
    
    @contextmanager
    def timer(self, name: str, tags: dict | None = None):
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            self.timing(name, duration_ms, tags)
    
    def _make_key(self, name: str, tags: dict | None = None) -> str:
        key = f"{self.CACHE_PREFIX}:{name}"
        if tags:
            tag_str = ":".join(f"{k}={v}" for k, v in sorted(tags.items()))
            key = f"{key}:{tag_str}"
        return key
    
    def get_counter(self, name: str, tags: dict | None = None) -> float:
        key = self._make_key(name, tags)
        return frappe.cache().get_value(key) or 0
    
    def get_gauge(self, name: str, tags: dict | None = None) -> dict | None:
        key = self._make_key(name, tags)
        return frappe.cache().get_value(key)
    
    def get_timing_stats(self, name: str, tags: dict | None = None) -> dict:
        key = self._make_key(f"{name}:timings", tags)
        timings = frappe.cache().get_value(key) or []
        
        if not timings:
            return {"count": 0}
        
        values = [t["value"] for t in timings]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }
    
    def _percentile(self, values: list[float], percentile: int) -> float:
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


metrics = MetricsCollector()


# eTax-specific metric helpers

def record_report_submission(tax_type: str, success: bool, duration_ms: float):
    """Record tax report submission metric"""
    metrics.increment("reports_total", tags={"tax_type": tax_type})
    if success:
        metrics.increment("reports_success", tags={"tax_type": tax_type})
    else:
        metrics.increment("reports_failed", tags={"tax_type": tax_type})
    metrics.timing("report_submission_latency", duration_ms, tags={"tax_type": tax_type})


def record_report_status_change(old_status: str, new_status: str):
    """Record report status change"""
    metrics.increment("status_changes", tags={"from": old_status, "to": new_status})


def record_draft_save(tax_type: str, success: bool):
    """Record draft save metric"""
    metrics.increment("drafts_saved_total", tags={"tax_type": tax_type})
    if success:
        metrics.increment("drafts_saved_success", tags={"tax_type": tax_type})


def record_deadline_approaching(tax_type: str, days_remaining: int):
    """Record deadline metric for monitoring"""
    metrics.gauge(
        "deadline_days_remaining",
        days_remaining,
        tags={"tax_type": tax_type}
    )


def record_api_call(endpoint: str, success: bool, duration_ms: float):
    """Record MTA API call metric"""
    metrics.increment("api_calls_total", tags={"endpoint": endpoint})
    if success:
        metrics.increment("api_calls_success", tags={"endpoint": endpoint})
    else:
        metrics.increment("api_calls_failed", tags={"endpoint": endpoint})
    metrics.timing("api_latency", duration_ms, tags={"endpoint": endpoint})


def record_error(error_type: str, tax_type: str | None = None):
    """Record error metric"""
    tags = {"type": error_type}
    if tax_type:
        tags["tax_type"] = tax_type
    metrics.increment("errors_total", tags=tags)


@frappe.whitelist()
def get_metrics_summary():
    """Get metrics summary for monitoring"""
    frappe.only_for(["System Manager", "Administrator"])
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reports": {
            "total": metrics.get_counter("reports_total"),
            "success": metrics.get_counter("reports_success"),
            "failed": metrics.get_counter("reports_failed"),
            "vat": metrics.get_counter("reports_total", tags={"tax_type": "03"}),
            "cit": metrics.get_counter("reports_total", tags={"tax_type": "01"})
        },
        "drafts": {
            "saved": metrics.get_counter("drafts_saved_total"),
            "success": metrics.get_counter("drafts_saved_success")
        },
        "submission_latency": metrics.get_timing_stats("report_submission_latency"),
        "api_latency": metrics.get_timing_stats("api_latency"),
        "errors": metrics.get_counter("errors_total")
    }
