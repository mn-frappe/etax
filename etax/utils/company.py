# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Company Integration Utilities for eTax

For multi-company support, use:

    from etax.mn_entity import get_entity_for_doc, get_etax_entity

    # From a document (preferred - ensures all apps use same entity)
    entity = get_entity_for_doc(sales_invoice)
    org_regno = entity.org_regno
    tin = entity.tin

    # From company name
    entity = get_etax_entity("ABC LLC")
"""

import frappe
from typing import Optional

# Re-export from mn_entity for convenience
from etax.mn_entity import (
    get_entity_for_doc,
    get_entity_for_company,
    get_etax_entity,
    get_ebarimt_entity,
    get_default_company,
    is_ebarimt_enabled,
    save_ent_id,
    MNEntity,
)

__all__ = [
    "get_entity_for_doc",
    "get_entity_for_company", 
    "get_etax_entity",
    "get_ebarimt_entity",
    "get_default_company",
    "is_ebarimt_enabled",
    "save_ent_id",
    "MNEntity",
    # Legacy functions below
    "get_org_info",
    "get_org_regno",
    "get_tin",
]


# =============================================================================
# Legacy functions (for backward compatibility)
# =============================================================================

def get_org_info(settings=None, company: Optional[str] = None, doc=None) -> dict:
    """
    DEPRECATED: Use get_entity_for_doc() or get_entity_for_company() instead.
    
    Get organization info. Priority:
    1. doc (if provided) - uses doc.company
    2. company (if provided) - uses directly
    3. settings.company (if settings has company link)
    4. Fall back to settings fields
    """
    # Determine company
    company_name = None
    
    if doc and hasattr(doc, "company"):
        company_name = doc.company
    elif company:
        company_name = company
    elif settings and hasattr(settings, "company"):
        company_name = settings.company
    
    # If we have a company, use the new method
    if company_name:
        try:
            entity = get_entity_for_company(company_name)
            return {
                "org_regno": entity.org_regno,
                "tin": entity.tin,
                "merchant_tin": entity.merchant_tin,
                "operator_tin": entity.operator_tin,
                "pos_no": entity.pos_no,
                "ent_id": entity.ent_id,
                "district_code": entity.district_code,
                "company": entity.company,
                "source": "company"
            }
        except Exception:
            pass
    
    # Fall back to settings fields
    result = {
        "org_regno": None,
        "tin": None,
        "merchant_tin": None,
        "operator_tin": None,
        "pos_no": None,
        "ent_id": None,
        "district_code": None,
        "company": None,
        "source": "settings"
    }
    
    if settings:
        result["org_regno"] = getattr(settings, "org_regno", None)
        result["merchant_tin"] = getattr(settings, "merchant_tin", None)
        result["operator_tin"] = getattr(settings, "operator_tin", None)
        result["pos_no"] = getattr(settings, "pos_no", None)
        result["district_code"] = getattr(settings, "district_code", None)
    
    return result


def get_org_regno(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get organization registry number (PIN)."""
    return get_org_info(settings, company, doc).get("org_regno")


def get_tin(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get TIN."""
    return get_org_info(settings, company, doc).get("tin")


def get_merchant_tin(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get merchant TIN."""
    return get_org_info(settings, company, doc).get("merchant_tin")


def get_operator_tin(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get operator TIN."""
    return get_org_info(settings, company, doc).get("operator_tin")


def get_pos_no(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get POS number."""
    return get_org_info(settings, company, doc).get("pos_no")


def save_ent_id_to_company(settings, ent_id: str) -> bool:
    """
    DEPRECATED: Use save_ent_id(company_name, ent_id) instead.
    """
    company_name = getattr(settings, "company", None)
    if company_name and ent_id:
        save_ent_id(company_name, ent_id)
        return True
    return False
