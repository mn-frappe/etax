# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Background Job Utilities for eTax

Provides async job wrappers with retry logic for non-blocking tax report operations.
"""

from typing import Any, Callable

import frappe
from frappe import _
from frappe.utils import now_datetime


def enqueue_with_retry(
    method: str | Callable,
    queue: str = "default",
    timeout: int = 300,
    max_retries: int = 3,
    retry_delay: int = 60,
    job_name: str | None = None,
    **kwargs
) -> str | None:
    """
    Enqueue a job with automatic retry on failure.
    """
    kwargs["_retry_count"] = kwargs.get("_retry_count", 0)
    kwargs["_max_retries"] = max_retries
    kwargs["_retry_delay"] = retry_delay
    kwargs["_original_method"] = method if isinstance(method, str) else f"{method.__module__}.{method.__name__}"
    
    job = frappe.enqueue(
        "etax.utils.background._execute_with_retry",
        queue=queue,
        timeout=timeout,
        job_name=job_name or f"etax_{now_datetime().strftime('%Y%m%d_%H%M%S')}",
        method=method,
        **kwargs
    )
    
    return job.id if job else None


def _execute_with_retry(method: str | Callable, **kwargs):
    """Execute method with retry logic"""
    retry_count = kwargs.pop("_retry_count", 0)
    max_retries = kwargs.pop("_max_retries", 3)
    retry_delay = kwargs.pop("_retry_delay", 60)
    original_method = kwargs.pop("_original_method", None)
    
    try:
        if isinstance(method, str):
            module_path, method_name = method.rsplit(".", 1)
            module = frappe.get_module(module_path)
            func = getattr(module, method_name)
        else:
            func = method
        
        result = func(**kwargs)
        
        frappe.logger("etax").info(
            f"Background job completed: {original_method or method}"
        )
        
        return result
        
    except Exception as e:
        frappe.logger("etax").error(
            f"Background job failed: {original_method or method}, "
            f"attempt {retry_count + 1}/{max_retries + 1}, error: {e}"
        )
        
        if retry_count < max_retries:
            frappe.enqueue(
                "etax.utils.background._execute_with_retry",
                queue="default",
                timeout=300,
                at_front=False,
                enqueue_after_commit=True,
                job_name=f"etax_retry_{retry_count + 1}",
                method=method,
                _retry_count=retry_count + 1,
                _max_retries=max_retries,
                _retry_delay=retry_delay,
                _original_method=original_method,
                **kwargs
            )
        else:
            frappe.log_error(
                title=f"eTax Job Failed: {original_method or method}",
                message=f"Max retries ({max_retries}) exceeded.\n\nError: {e}\n\nKwargs: {kwargs}"
            )
            _notify_job_failure(original_method or str(method), str(e), kwargs)
        
        raise


def _notify_job_failure(method: str, error: str, kwargs: dict):
    """Send notification about job failure"""
    try:
        admins = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager", "parenttype": "User"},
            pluck="parent"
        )
        
        for admin in admins[:3]:
            frappe.publish_realtime(
                "msgprint",
                {
                    "message": _(
                        "eTax background job failed after max retries: {0}"
                    ).format(method),
                    "indicator": "red"
                },
                user=admin
            )
    except Exception:
        pass


# Convenience functions for eTax operations

def enqueue_report_submission(report_name: str, **kwargs):
    """Enqueue eTax report submission"""
    return enqueue_with_retry(
        "etax.api.client.submit_report_async",
        queue="long",
        timeout=600,
        max_retries=3,
        retry_delay=120,
        job_name=f"etax_submit_{report_name}",
        report_name=report_name,
        **kwargs
    )


def enqueue_report_save(report_name: str, **kwargs):
    """Enqueue eTax report save (draft)"""
    return enqueue_with_retry(
        "etax.api.client.save_report_async",
        queue="default",
        timeout=300,
        max_retries=2,
        retry_delay=60,
        job_name=f"etax_save_{report_name}",
        report_name=report_name,
        **kwargs
    )


def enqueue_report_list_sync(ent_id: str, **kwargs):
    """Enqueue sync of pending reports list"""
    return enqueue_with_retry(
        "etax.api.client.sync_report_list_async",
        queue="short",
        timeout=120,
        max_retries=2,
        retry_delay=60,
        job_name=f"etax_list_sync_{ent_id}",
        ent_id=ent_id,
        **kwargs
    )


def enqueue_orgs_sync(**kwargs):
    """Enqueue user organizations sync"""
    return enqueue_with_retry(
        "etax.api.client.sync_user_orgs_async",
        queue="short",
        timeout=120,
        max_retries=2,
        retry_delay=60,
        job_name="etax_orgs_sync",
        **kwargs
    )


def enqueue_vat_report_generation(company: str, year: int, month: int, **kwargs):
    """Enqueue VAT report generation from GL entries"""
    return enqueue_with_retry(
        "etax.api.transformer.generate_vat_report_async",
        queue="default",
        timeout=600,
        max_retries=2,
        retry_delay=120,
        job_name=f"etax_vat_gen_{company}_{year}_{month}",
        company=company,
        year=year,
        month=month,
        **kwargs
    )


# Job status tracking

def get_job_status(job_id: str) -> dict:
    """Get status of a background job"""
    try:
        from frappe.utils.background_jobs import get_job
        job = get_job(job_id)
        if job:
            return {
                "id": job_id,
                "status": job.get_status(),
                "result": job.result if job.is_finished else None,
                "error": str(job.exc_info) if job.is_failed else None
            }
    except Exception:
        pass
    
    return {"id": job_id, "status": "unknown"}


def cancel_job(job_id: str) -> bool:
    """Cancel a pending background job"""
    try:
        from rq import cancel_job as rq_cancel
        rq_cancel(job_id, connection=frappe.cache())
        return True
    except Exception:
        return False
