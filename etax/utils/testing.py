# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Test Utilities for eTax

Provides mock fixtures, test helpers, and factory functions for testing.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any
from unittest.mock import MagicMock, patch

import frappe


@dataclass
class MockResponse:
    """Mock HTTP response"""
    status_code: int = 200
    content: bytes | str = b""
    headers: dict = field(default_factory=dict)
    text: str = field(init=False, default="")
    
    def __post_init__(self):
        if isinstance(self.content, str):
            self.content = self.content.encode("utf-8")
        self.text = bytes(self.content).decode("utf-8")
    
    def json(self) -> dict:
        return json.loads(self.content)
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class ETaxMockClient:
    """
    Mock eTax API client for testing.
    
    Usage:
        with ETaxMockClient() as mock_client:
            mock_client.set_response("submit_report", {"success": True, "reportId": "123"})
            
            result = submit_tax_report(data)
            assert result["success"]
    """
    
    def __init__(self):
        self._responses: dict[str, Any] = {}
        self._calls: dict[str, list] = {}
        self._patch = None
    
    def set_response(self, method: str, response: Any):
        self._responses[method] = response
    
    def set_error(self, method: str, error: Exception):
        self._responses[method] = error
    
    def call_count(self, method: str) -> int:
        return len(self._calls.get(method, []))
    
    def get_calls(self, method: str) -> list:
        return self._calls.get(method, [])
    
    def _record_call(self, method: str, *args, **kwargs):
        if method not in self._calls:
            self._calls[method] = []
        self._calls[method].append({"args": args, "kwargs": kwargs})
    
    def _get_response(self, method: str):
        response = self._responses.get(method)
        if isinstance(response, Exception):
            raise response
        return response or {"success": True}
    
    def __enter__(self):
        self._patch = patch("etax.etax.api_client.ETaxClient")
        mock_class = self._patch.start()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        def make_mock_method(method_name):
            def mock_method(*args, **kwargs):
                self._record_call(method_name, *args, **kwargs)
                return self._get_response(method_name)
            return mock_method
        
        for method in ["submit_report", "save_draft", "get_report_status", "get_tax_types", "test_connection"]:
            setattr(mock_instance, method, make_mock_method(method))
        
        return self
    
    def __exit__(self, *args):
        if self._patch:
            self._patch.stop()


# Test data factories

def make_vat_report_data(
    ent_id: str = "1234567",
    year: int = 2024,
    period: int = 1,
    **kwargs
) -> dict:
    """Create test VAT report data"""
    return {
        "ent_id": ent_id,
        "tax_type_code": "03",  # VAT
        "form_no": "TT-01",
        "year": year,
        "period": period,
        "vat_sales": kwargs.get("vat_sales", 10000000),
        "vat_output": kwargs.get("vat_output", 1000000),
        "vat_purchases": kwargs.get("vat_purchases", 8000000),
        "vat_input": kwargs.get("vat_input", 800000),
        "vat_payable": kwargs.get("vat_payable", 200000),
        **{k: v for k, v in kwargs.items() if k not in ["vat_sales", "vat_output", "vat_purchases", "vat_input", "vat_payable"]}
    }


def make_income_tax_report_data(
    ent_id: str = "1234567",
    year: int = 2024,
    period: int = 0,  # Annual
    **kwargs
) -> dict:
    """Create test income tax report data"""
    return {
        "ent_id": ent_id,
        "tax_type_code": "01",  # Corporate Income Tax
        "form_no": "AA-01",
        "year": year,
        "period": period,
        "total_income": kwargs.get("total_income", 100000000),
        "deductions": kwargs.get("deductions", 80000000),
        "taxable_income": kwargs.get("taxable_income", 20000000),
        "tax_rate": kwargs.get("tax_rate", 0.25),
        "tax_amount": kwargs.get("tax_amount", 5000000),
        **{k: v for k, v in kwargs.items() if k not in ["total_income", "deductions", "taxable_income", "tax_rate", "tax_amount"]}
    }


def make_report_submission_response(
    success: bool = True,
    report_id: str = "RPT123456",
    status: str = "Submitted",
    **kwargs
) -> dict:
    """Create mock report submission response"""
    if not success:
        return {
            "success": False,
            "errorCode": kwargs.get("error_code", "ERR001"),
            "message": kwargs.get("message", "Test error")
        }
    
    return {
        "success": True,
        "reportId": report_id,
        "status": status,
        "submittedAt": datetime.now().isoformat(),
        "reference": kwargs.get("reference", f"REF-{report_id}"),
        **kwargs
    }


def make_entity_data(
    ent_id: str = "1234567",
    ent_name: str = "Test Company LLC",
    **kwargs
) -> dict:
    """Create test entity data"""
    return {
        "ent_id": ent_id,
        "ent_name": ent_name,
        "state_reg_number": kwargs.get("state_reg_number", ent_id),
        "tax_office": kwargs.get("tax_office", "UB-01"),
        **kwargs
    }


# Test fixtures

class TestFixtures:
    """Test fixtures for eTax"""
    
    @staticmethod
    def create_test_settings(
        enabled: bool = True,
        api_url: str = "https://test.etax.mta.mn",
        api_key: str = "test_key_123",
        certificate_expiry: str | None = None
    ) -> None:
        """Create or update test settings"""
        try:
            settings = frappe.get_single("eTax Settings")
        except frappe.DoesNotExistError:
            settings = frappe.new_doc("eTax Settings")
        
        setattr(settings, "enabled", enabled)
        setattr(settings, "api_url", api_url)
        setattr(settings, "api_key", api_key)
        
        if certificate_expiry:
            setattr(settings, "certificate_expiry", certificate_expiry)
        
        settings.save(ignore_permissions=True)
    
    @staticmethod
    def create_test_report(
        tax_type: str = "03",
        year: int = 2024,
        period: int = 1,
        status: str = "Draft",
        **kwargs
    ) -> str | None:
        """Create test tax report"""
        if not frappe.db.table_exists("eTax Report"):
            return None
        
        doc = frappe.get_doc({
            "doctype": "eTax Report",
            "tax_type_code": tax_type,
            "year": year,
            "period": period,
            "status": status,
            **kwargs
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    
    @staticmethod
    def cleanup():
        """Clean up test data"""
        if frappe.db.table_exists("eTax Report"):
            frappe.db.delete("eTax Report", {"owner": "test@example.com"})
        frappe.db.commit()


# Assertion helpers

def assert_report_valid(report_data: dict):
    """Assert report data is valid"""
    assert "ent_id" in report_data
    assert "tax_type_code" in report_data
    assert "year" in report_data
    assert "period" in report_data


def assert_api_called(mock_client: ETaxMockClient, method: str, times: int = 1):
    actual = mock_client.call_count(method)
    assert actual == times, f"Expected {method} to be called {times} times, got {actual}"


# Context managers

class DisabledCircuitBreaker:
    """Disable circuit breaker during tests"""
    
    def __enter__(self):
        self._patch = patch("etax.utils.resilience.etax_circuit_breaker")
        mock_cb = self._patch.start()
        mock_cb.call.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
        return mock_cb
    
    def __exit__(self, *args):
        self._patch.stop()


class MockedCertificate:
    """Mock digital certificate for testing"""
    
    def __init__(self, valid: bool = True, days_remaining: int = 365):
        self.valid = valid
        self.days_remaining = days_remaining
    
    def __enter__(self):
        from datetime import timedelta
        expiry = date.today() + timedelta(days=self.days_remaining) if self.valid else date.today() - timedelta(days=1)
        
        self._patch = patch("frappe.get_single")
        mock_get = self._patch.start()
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.certificate_expiry = expiry.isoformat()
        mock_get.return_value = mock_settings
        return self
    
    def __exit__(self, *args):
        self._patch.stop()
