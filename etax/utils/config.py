# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Configuration Validation for eTax

Validates required settings on startup and provides configuration helpers.
"""

from dataclasses import dataclass
from datetime import datetime

import frappe
from frappe import _


@dataclass
class ConfigIssue:
    """Configuration issue"""
    field: str
    message: str
    severity: str = "error"


@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    issues: list[ConfigIssue]
    
    def get_errors(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "error"]
    
    def get_warnings(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "warning"]


class ConfigValidator:
    """Validates eTax configuration"""
    
    SETTINGS_DOCTYPE = "eTax Settings"
    
    def validate(self) -> ConfigValidationResult:
        """Validate all configuration"""
        issues: list[ConfigIssue] = []
        
        if not self._settings_exist():
            issues.append(ConfigIssue(
                field="settings",
                message=_("eTax Settings not found. Please configure the app."),
                severity="error"
            ))
            return ConfigValidationResult(is_valid=False, issues=issues)
        
        settings = frappe.get_single(self.SETTINGS_DOCTYPE)
        
        issues.extend(self._validate_api_config(settings))
        issues.extend(self._validate_auth_config(settings))
        issues.extend(self._validate_certificate(settings))
        issues.extend(self._validate_company_config(settings))
        issues.extend(self._validate_environment())
        
        is_valid = len([i for i in issues if i.severity == "error"]) == 0
        return ConfigValidationResult(is_valid=is_valid, issues=issues)
    
    def _settings_exist(self) -> bool:
        try:
            frappe.get_single(self.SETTINGS_DOCTYPE)
            return True
        except Exception:
            return False
    
    def _validate_api_config(self, settings) -> list[ConfigIssue]:
        issues = []
        
        if not settings.enabled:
            issues.append(ConfigIssue(
                field="enabled",
                message=_("eTax integration is disabled"),
                severity="info"
            ))
            return issues
        
        if not settings.api_url:
            issues.append(ConfigIssue(
                field="api_url",
                message=_("MTA API URL is required"),
                severity="error"
            ))
        elif not settings.api_url.startswith("https://"):
            issues.append(ConfigIssue(
                field="api_url",
                message=_("API URL should use HTTPS for security"),
                severity="warning"
            ))
        
        return issues
    
    def _validate_auth_config(self, settings) -> list[ConfigIssue]:
        issues = []
        
        if not settings.enabled:
            return issues
        
        if not settings.get_password("api_key"):
            issues.append(ConfigIssue(
                field="api_key",
                message=_("API key is required for MTA authentication"),
                severity="error"
            ))
        
        return issues
    
    def _validate_certificate(self, settings) -> list[ConfigIssue]:
        """Validate digital certificate for MTA submissions"""
        issues = []
        
        if not getattr(settings, "enabled", False):
            return issues
        
        # Check certificate expiry
        cert_expiry = getattr(settings, "certificate_expiry", None)
        if cert_expiry:
            from frappe.utils import get_datetime
            expiry_dt = get_datetime(cert_expiry)
            if expiry_dt:
                expiry = expiry_dt.date()
                today = datetime.now().date()
                days_remaining = (expiry - today).days
                
                if days_remaining < 0:
                    issues.append(ConfigIssue(
                        field="certificate_expiry",
                        message=_("Digital certificate has EXPIRED. Tax submissions will fail."),
                        severity="error"
                    ))
                elif days_remaining < 30:
                    issues.append(ConfigIssue(
                        field="certificate_expiry",
                        message=_("Digital certificate expires in {0} days. Please renew soon.").format(days_remaining),
                        severity="warning"
                    ))
                elif days_remaining < 90:
                    issues.append(ConfigIssue(
                        field="certificate_expiry",
                        message=_("Digital certificate expires in {0} days.").format(days_remaining),
                        severity="info"
                    ))
        else:
            issues.append(ConfigIssue(
                field="certificate_expiry",
                message=_("Certificate expiry date not set. Cannot track certificate validity."),
                severity="warning"
            ))
        
        return issues
    
    def _validate_company_config(self, settings) -> list[ConfigIssue]:
        issues = []
        
        if not settings.enabled:
            return issues
        
        # Check entity mappings
        if hasattr(settings, "entity_mappings"):
            if not settings.entity_mappings or len(settings.entity_mappings) == 0:
                issues.append(ConfigIssue(
                    field="entity_mappings",
                    message=_("No company to entity ID mappings configured"),
                    severity="warning"
                ))
        
        return issues
    
    def _validate_environment(self) -> list[ConfigIssue]:
        issues = []
        
        try:
            frappe.cache().set_value("etax:config_test", "ok", expires_in_sec=5)
            frappe.cache().delete_value("etax:config_test")
        except Exception as e:
            issues.append(ConfigIssue(
                field="redis",
                message=_("Redis connectivity issue: {0}").format(str(e)),
                severity="warning"
            ))
        
        return issues


def validate_config() -> ConfigValidationResult:
    return ConfigValidator().validate()


def validate_config_on_startup():
    """Hook for startup validation"""
    try:
        result = validate_config()
        
        if not result.is_valid:
            for issue in result.get_errors():
                frappe.logger("etax").error(f"Config error - {issue.field}: {issue.message}")
        
        for issue in result.get_warnings():
            frappe.logger("etax").warning(f"Config warning - {issue.field}: {issue.message}")
    except Exception as e:
        frappe.logger("etax").error(f"Config validation failed: {e}")


def get_config_status() -> dict:
    result = validate_config()
    return {
        "valid": result.is_valid,
        "errors": [{"field": i.field, "message": i.message} for i in result.get_errors()],
        "warnings": [{"field": i.field, "message": i.message} for i in result.get_warnings()]
    }


@frappe.whitelist()
def check_configuration():
    """Check eTax configuration status"""
    frappe.only_for(["System Manager", "Administrator"])
    return get_config_status()
