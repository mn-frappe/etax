# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Validation Utilities for eTax

Provides data validation for tax reports before submission to MTA.
Ensures data integrity and compliance.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import frappe
from frappe import _


@dataclass
class ValidationError:
    """Single validation error"""
    field: str
    message: str
    code: str = "invalid"
    value: Any = None


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: list[ValidationError]
    
    def raise_if_invalid(self):
        if not self.is_valid:
            error_messages = [f"{e.field}: {e.message}" for e in self.errors]
            frappe.throw(
                _("Validation failed: {0}").format("; ".join(error_messages)),
                title=_("eTax Validation Error")
            )


class Validator:
    """Chainable field validator"""
    
    def __init__(self):
        self._errors: list[ValidationError] = []
        self._current_field: str | None = None
        self._current_value: Any = None
        self._skip_remaining = False
    
    def field(self, name: str, value: Any) -> "Validator":
        self._current_field = name
        self._current_value = value
        self._skip_remaining = False
        return self
    
    def _add_error(self, message: str, code: str = "invalid"):
        self._errors.append(ValidationError(
            field=self._current_field or "unknown",
            message=message,
            code=code,
            value=self._current_value
        ))
    
    def required(self, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if self._current_value is None or self._current_value == "":
            self._add_error(message or _("This field is required"), "required")
            self._skip_remaining = True
        return self
    
    def optional(self) -> "Validator":
        if self._current_value is None or self._current_value == "":
            self._skip_remaining = True
        return self
    
    def regex(self, pattern: str, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if not re.match(pattern, str(self._current_value)):
            self._add_error(message or _("Invalid format"), "format")
        return self
    
    def min_length(self, length: int, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if len(str(self._current_value)) < length:
            self._add_error(message or _("Must be at least {0} characters").format(length), "min_length")
        return self
    
    def max_length(self, length: int, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if len(str(self._current_value)) > length:
            self._add_error(message or _("Must be at most {0} characters").format(length), "max_length")
        return self
    
    def between(self, min_val: float, max_val: float, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        try:
            val = float(self._current_value)
            if val < min_val or val > max_val:
                self._add_error(message or _("Must be between {0} and {1}").format(min_val, max_val), "range")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def positive(self, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        try:
            if float(self._current_value) <= 0:
                self._add_error(message or _("Must be positive"), "positive")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def non_negative(self, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        try:
            if float(self._current_value) < 0:
                self._add_error(message or _("Must be non-negative"), "non_negative")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def is_decimal(self, max_places: int = 2, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        try:
            dec = Decimal(str(self._current_value))
            exponent = dec.as_tuple().exponent
            if isinstance(exponent, int) and exponent < -max_places:
                self._add_error(
                    message or _("Maximum {0} decimal places allowed").format(max_places),
                    "decimal_places"
                )
        except InvalidOperation:
            self._add_error(_("Invalid decimal number"), "decimal")
        return self
    
    def in_list(self, valid_values: list, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if self._current_value not in valid_values:
            self._add_error(
                message or _("Must be one of: {0}").format(", ".join(str(v) for v in valid_values)),
                "choices"
            )
        return self
    
    def is_date(self, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if isinstance(self._current_value, (date, datetime)):
            return self
        try:
            if isinstance(self._current_value, str):
                datetime.strptime(self._current_value, "%Y-%m-%d")
        except ValueError:
            self._add_error(message or _("Must be a valid date (YYYY-MM-DD)"), "date")
        return self
    
    def custom(self, validator_func: Callable[[Any], bool], message: str) -> "Validator":
        if self._skip_remaining:
            return self
        if not validator_func(self._current_value):
            self._add_error(message, "custom")
        return self
    
    def validate(self) -> ValidationResult:
        return ValidationResult(
            is_valid=len(self._errors) == 0,
            errors=self._errors.copy()
        )


# eTax-specific validators

def validate_entity_id(ent_id: str) -> ValidationResult:
    """Validate Mongolian entity ID (7 digits)"""
    return (Validator()
        .field("ent_id", ent_id)
        .required()
        .regex(r"^\d{7}$", _("Entity ID must be exactly 7 digits"))
        .validate())


def validate_tax_type_code(tax_type_code: str) -> ValidationResult:
    """Validate eTax tax type code"""
    # Common Mongolian tax types
    valid_codes = [
        "01",  # Corporate Income Tax
        "02",  # Personal Income Tax
        "03",  # VAT
        "04",  # Excise Tax
        "05",  # Customs Duty
        "06",  # Stamp Duty
        "07",  # Real Estate Tax
        "08",  # Vehicle Tax
        "09",  # Land Fee
        "10",  # Social Insurance
        "11",  # Health Insurance
    ]
    
    return (Validator()
        .field("tax_type_code", tax_type_code)
        .required()
        .in_list(valid_codes, _("Invalid tax type code"))
        .validate())


def validate_report_period(year: int, period: int, period_type: str = "monthly") -> ValidationResult:
    """Validate tax report period"""
    v = Validator()
    current_year = datetime.now().year
    
    v.field("year", year).required().between(2000, current_year + 1)
    
    if period_type == "monthly":
        v.field("period", period).required().between(1, 12, _("Month must be 1-12"))
    elif period_type == "quarterly":
        v.field("period", period).required().between(1, 4, _("Quarter must be 1-4"))
    elif period_type == "annual":
        v.field("period", period).required().in_list([0, 1], _("Annual period must be 0 or 1"))
    
    return v.validate()


def validate_form_data(form_no: str, data: dict) -> ValidationResult:
    """Validate tax form data based on form number"""
    v = Validator()
    
    v.field("form_no", form_no).required()
    
    # Common fields across all forms
    v.field("ent_id", data.get("ent_id")).required().regex(r"^\d{7}$")
    v.field("year", data.get("year")).required()
    v.field("period", data.get("period")).required()
    
    # Form-specific validation
    if form_no.startswith("TT"):  # VAT forms
        v.field("vat_sales", data.get("vat_sales", 0)).optional().non_negative()
        v.field("vat_purchases", data.get("vat_purchases", 0)).optional().non_negative()
        v.field("vat_payable", data.get("vat_payable", 0)).optional()
    
    elif form_no.startswith("AA"):  # Income tax forms
        v.field("total_income", data.get("total_income", 0)).optional().non_negative()
        v.field("deductions", data.get("deductions", 0)).optional().non_negative()
        v.field("taxable_income", data.get("taxable_income", 0)).optional().non_negative()
    
    return v.validate()


def validate_report_submission(data: dict) -> ValidationResult:
    """Validate complete eTax report submission data"""
    v = Validator()
    
    # Entity info
    v.field("ent_id", data.get("ent_id")).required().regex(r"^\d{7}$")
    v.field("ent_name", data.get("ent_name")).optional().max_length(200)
    
    # Report identification
    v.field("tax_type_code", data.get("tax_type_code")).required()
    v.field("form_no", data.get("form_no")).required()
    v.field("year", data.get("year")).required().between(2000, datetime.now().year + 1)
    v.field("period", data.get("period")).required().between(0, 12)
    
    # Dates
    if data.get("report_date"):
        v.field("report_date", data["report_date"]).is_date()
    if data.get("due_date"):
        v.field("due_date", data["due_date"]).is_date()
    
    # Amounts (if present)
    if "total_amount" in data:
        v.field("total_amount", data["total_amount"]).non_negative().is_decimal(2)
    if "tax_amount" in data:
        v.field("tax_amount", data["tax_amount"]).is_decimal(2)
    
    return v.validate()


def validate_payment_data(data: dict) -> ValidationResult:
    """Validate tax payment data"""
    v = Validator()
    
    v.field("ent_id", data.get("ent_id")).required().regex(r"^\d{7}$")
    v.field("tax_type_code", data.get("tax_type_code")).required()
    v.field("amount", data.get("amount")).required().positive().is_decimal(2)
    v.field("payment_date", data.get("payment_date")).required().is_date()
    
    # Bank info
    v.field("bank_account", data.get("bank_account")).optional().regex(
        r"^\d{10,16}$", _("Invalid bank account number")
    )
    
    return v.validate()


# Certificate validation (for digital signatures)

def validate_certificate(cert_data: dict) -> ValidationResult:
    """Validate digital certificate data for MTA submission"""
    v = Validator()
    
    v.field("cert_number", cert_data.get("cert_number")).required()
    v.field("cert_expiry", cert_data.get("cert_expiry")).required().is_date()
    
    # Check expiry
    if cert_data.get("cert_expiry"):
        try:
            expiry = datetime.strptime(cert_data["cert_expiry"], "%Y-%m-%d").date()
            v.field("cert_expiry", cert_data["cert_expiry"]).custom(
                lambda x: expiry > date.today(),
                _("Certificate has expired")
            )
        except ValueError:
            pass
    
    return v.validate()


# Helper
def validate_or_throw(result: ValidationResult):
    result.raise_if_invalid()
