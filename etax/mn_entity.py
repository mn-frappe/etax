# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Multi-Company Entity Resolver for MN Apps

This module provides a unified way to get entity configuration (TIN, merchant info, etc.)
based on the Company from a document. All MN apps (eTax, eBarimt, QPay, eBalance) should
use this module to ensure they're all talking about the SAME entity.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                      Sales Invoice                               │
    │                      company: "ABC LLC"                          │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    get_entity_for_doc()                          │
    │            Resolves company → entity config                      │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     Company: "ABC LLC"                           │
    │  ┌────────────────────────────────────────────────────────────┐ │
    │  │ tax_id (PIN): "6709389"                                    │ │
    │  │ custom_tin: "15200005097"                                  │ │
    │  │ custom_merchant_tin: "15200005097"                         │ │
    │  │ custom_operator_tin: "15200005097"                         │ │
    │  │ custom_pos_no: "10003470"                                  │ │
    │  │ custom_district_code: "23"                                 │ │
    │  │ custom_ent_id: "12345"                                     │ │
    │  │ custom_ebarimt_enabled: 1                                  │ │
    │  └────────────────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    from mn_entity import get_entity_for_doc, get_entity_for_company

    # From a document (preferred)
    doc = frappe.get_doc("Sales Invoice", "SINV-00001")
    entity = get_entity_for_doc(doc)
    
    # Or from company name directly
    entity = get_entity_for_company("ABC LLC")
    
    # Access entity info
    tin = entity.tin
    merchant_tin = entity.merchant_tin
    org_regno = entity.org_regno  # same as tax_id/PIN

Entity Object Properties:
    - company: Company name
    - org_regno: Organization registry number (PIN) - Company.tax_id
    - tin: Taxpayer Identification Number - Company.custom_tin
    - ent_id: MTA Entity ID - Company.custom_ent_id
    - merchant_tin: eBarimt Merchant TIN - Company.custom_merchant_tin
    - operator_tin: eBarimt Operator TIN - Company.custom_operator_tin
    - pos_no: eBarimt POS Number - Company.custom_pos_no
    - district_code: Default District - Company.custom_district_code
    - ebarimt_enabled: Is eBarimt enabled - Company.custom_ebarimt_enabled
"""

import frappe
from frappe import _
from typing import Optional, Union, Any
from dataclasses import dataclass


@dataclass
class MNEntity:
    """
    Represents a Mongolian business entity with all tax-related identifiers.
    
    This is the unified entity object that all MN apps should use.
    """
    company: str
    org_regno: Optional[str] = None      # PIN / Registry Number (Company.tax_id)
    tin: Optional[str] = None            # TIN (Company.custom_tin)
    ent_id: Optional[str] = None         # MTA Entity ID (Company.custom_ent_id)
    merchant_tin: Optional[str] = None   # eBarimt Merchant TIN
    operator_tin: Optional[str] = None   # eBarimt Operator TIN
    pos_no: Optional[str] = None         # eBarimt POS Number
    district_code: Optional[str] = None  # Default District Code
    ebarimt_enabled: bool = False        # Is eBarimt enabled for this company
    
    def validate(self, require_ebarimt: bool = False) -> None:
        """
        Validate that required fields are present.
        
        Raises:
            frappe.ValidationError: If required fields are missing
        """
        if not self.org_regno:
            frappe.throw(
                _("Company {0} does not have Tax ID (PIN) configured").format(self.company),
                title=_("Missing Tax ID")
            )
        
        if require_ebarimt:
            if not self.merchant_tin:
                frappe.throw(
                    _("Company {0} does not have Merchant TIN configured").format(self.company),
                    title=_("Missing Merchant TIN")
                )
            if not self.pos_no:
                frappe.throw(
                    _("Company {0} does not have POS Number configured").format(self.company),
                    title=_("Missing POS Number")
                )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "company": self.company,
            "org_regno": self.org_regno,
            "tin": self.tin,
            "ent_id": self.ent_id,
            "merchant_tin": self.merchant_tin,
            "operator_tin": self.operator_tin,
            "pos_no": self.pos_no,
            "district_code": self.district_code,
            "ebarimt_enabled": self.ebarimt_enabled,
        }


def get_entity_for_company(company_name: str) -> MNEntity:
    """
    Get MN entity configuration for a specific company.
    
    Args:
        company_name: ERPNext Company name
        
    Returns:
        MNEntity object with all tax identifiers
        
    Raises:
        frappe.DoesNotExistError: If company doesn't exist
    """
    if not company_name:
        frappe.throw(_("Company is required"), title=_("Missing Company"))
    
    company = frappe.get_cached_doc("Company", company_name)
    
    return MNEntity(
        company=company_name,
        org_regno=company.tax_id or None,  # type: ignore
        tin=getattr(company, "custom_tin", None),
        ent_id=getattr(company, "custom_ent_id", None),
        merchant_tin=getattr(company, "custom_merchant_tin", None),
        operator_tin=getattr(company, "custom_operator_tin", None),
        pos_no=getattr(company, "custom_pos_no", None),
        district_code=getattr(company, "custom_district_code", None),
        ebarimt_enabled=bool(getattr(company, "custom_ebarimt_enabled", False)),
    )


def get_entity_for_doc(doc: Any, doctype: Optional[str] = None) -> MNEntity:
    """
    Get MN entity configuration from a document's company.
    
    This is the PRIMARY method all MN apps should use. It ensures that
    all apps use the same company/entity for a given document.
    
    Args:
        doc: Document object or document name
        doctype: DocType name (required if doc is a string)
        
    Returns:
        MNEntity object with all tax identifiers
        
    Example:
        # From document object
        sinv = frappe.get_doc("Sales Invoice", "SINV-00001")
        entity = get_entity_for_doc(sinv)
        
        # From document name
        entity = get_entity_for_doc("SINV-00001", "Sales Invoice")
    """
    # Get document if string passed
    if isinstance(doc, str):
        if not doctype:
            frappe.throw(_("DocType is required when passing document name"))
        doc = frappe.get_doc(doctype, doc)  # type: ignore
    
    # Get company from document
    company_name = getattr(doc, "company", None)
    
    if not company_name:
        frappe.throw(
            _("{0} {1} does not have a company").format(doc.doctype, doc.name),
            title=_("Missing Company")
        )
    
    return get_entity_for_company(company_name)  # type: ignore


def save_ent_id(company_name: str, ent_id: str) -> None:
    """
    Save MTA Entity ID to Company after successful MTA registration/login.
    
    Args:
        company_name: ERPNext Company name
        ent_id: Entity ID from MTA
    """
    if company_name and ent_id:
        frappe.db.set_value("Company", company_name, "custom_ent_id", ent_id)
        frappe.clear_cache(doctype="Company")


def get_default_company() -> Optional[str]:
    """
    Get the default company for single-company setups or current user's default.
    
    Returns:
        Company name or None
    """
    # Try user's default company
    default = frappe.defaults.get_user_default("company")  # type: ignore
    if default:
        return default
    
    # Try global default
    default = frappe.defaults.get_global_default("company")  # type: ignore
    if default:
        return default
    
    # If only one company exists, use it
    companies = frappe.get_all("Company", limit=2)
    if len(companies) == 1:
        return companies[0].name
    
    return None


# =============================================================================
# Convenience functions for specific apps
# =============================================================================

def get_etax_entity(doc_or_company) -> MNEntity:
    """
    Get entity for eTax operations.
    
    Args:
        doc_or_company: Document object or company name
        
    Returns:
        MNEntity with org_regno and tin validated
    """
    if isinstance(doc_or_company, str) and frappe.db.exists("Company", doc_or_company):
        entity = get_entity_for_company(doc_or_company)
    else:
        entity = get_entity_for_doc(doc_or_company)
    
    entity.validate()
    return entity


def get_ebarimt_entity(doc_or_company) -> MNEntity:
    """
    Get entity for eBarimt operations.
    
    Args:
        doc_or_company: Document object or company name
        
    Returns:
        MNEntity with merchant info validated
    """
    if isinstance(doc_or_company, str) and frappe.db.exists("Company", doc_or_company):
        entity = get_entity_for_company(doc_or_company)
    else:
        entity = get_entity_for_doc(doc_or_company)
    
    entity.validate(require_ebarimt=True)
    return entity


def is_ebarimt_enabled(company_name: str) -> bool:
    """
    Check if eBarimt is enabled for a company.
    
    Args:
        company_name: ERPNext Company name
        
    Returns:
        True if eBarimt is enabled for this company
    """
    try:
        return bool(frappe.db.get_value("Company", company_name, "custom_ebarimt_enabled"))
    except Exception:
        return False


# =============================================================================
# API for JavaScript
# =============================================================================

@frappe.whitelist()
def get_entity_info(company: Optional[str] = None, doctype: Optional[str] = None, docname: Optional[str] = None) -> dict:
    """
    Get entity info for JavaScript.
    
    Can be called with either:
    - company: Company name directly
    - doctype + docname: Get company from document
    
    Returns:
        dict with entity info
    """
    if doctype and docname:
        entity = get_entity_for_doc(docname, doctype)
    elif company:
        entity = get_entity_for_company(company)
    else:
        company = get_default_company()
        if company:
            entity = get_entity_for_company(company)
        else:
            return {"error": "No company specified"}
    
    return entity.to_dict()
