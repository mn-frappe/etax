# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Journal Entry Integration

Captures VAT adjustments from Journal Entries for tax reporting.
This handles:
- VAT corrections
- VAT adjustments between periods
- Manual VAT entries
"""

import frappe
from frappe import _
from frappe.utils import flt


def on_submit(doc, method=None):
    """
    Handle Journal Entry submission - capture VAT adjustments.
    
    Args:
        doc: Journal Entry document
        method: Event method name
    """
    if not _is_etax_vat_sync_enabled():
        return
    
    # Check if this JE affects VAT accounts
    vat_entries = _get_vat_account_entries(doc)
    
    if not vat_entries:
        return
    
    # Create adjustment record
    _create_vat_adjustment(doc, vat_entries)


def on_cancel(doc, method=None):
    """
    Handle Journal Entry cancellation.
    
    Args:
        doc: Journal Entry document
        method: Event method name
    """
    if not _is_etax_vat_sync_enabled():
        return
    
    # Mark linked adjustments as cancelled
    adjustments = frappe.get_all(
        "eTax Invoice Link",
        filters={
            "reference_doctype": "Journal Entry",
            "reference_name": doc.name,
            "status": ["!=", "Submitted"]
        },
        pluck="name"
    )
    
    for adj_name in adjustments:
        frappe.db.set_value(
            "eTax Invoice Link",
            adj_name,
            "status",
            "Cancelled"
        )


def _get_vat_account_entries(doc):
    """
    Get Journal Entry accounts that are VAT accounts.
    
    Args:
        doc: Journal Entry document
        
    Returns:
        list: VAT account entries with amounts
    """
    vat_accounts = _get_vat_accounts(doc.company)
    
    if not vat_accounts:
        return []
    
    vat_entries = []
    
    for account in doc.accounts:
        if account.account in vat_accounts:
            vat_type = vat_accounts[account.account]
            vat_entries.append({
                "account": account.account,
                "vat_type": vat_type,
                "debit": flt(account.debit),
                "credit": flt(account.credit),
                "party_type": account.party_type,
                "party": account.party
            })
    
    return vat_entries


def _get_vat_accounts(company):
    """
    Get VAT accounts for a company from eTax Settings.
    
    Args:
        company: Company name
        
    Returns:
        dict: Account name -> VAT type mapping
    """
    try:
        settings = frappe.get_cached_doc("eTax Settings")
        
        vat_accounts = {}
        
        # Output VAT account
        if settings.vat_output_account:
            vat_accounts[settings.vat_output_account] = "Output"
        
        # Input VAT account
        if settings.vat_input_account:
            vat_accounts[settings.vat_input_account] = "Input"
        
        # If no settings, try to find VAT accounts by name pattern
        if not vat_accounts:
            accounts = frappe.get_all(
                "Account",
                filters={
                    "company": company,
                    "account_type": "Tax",
                    "is_group": 0
                },
                fields=["name", "account_name"]
            )
            
            for acc in accounts:
                name_lower = acc.account_name.lower()
                if any(kw in name_lower for kw in ["output vat", "нөат борлуулалт", "vat payable"]):
                    vat_accounts[acc.name] = "Output"
                elif any(kw in name_lower for kw in ["input vat", "нөат авлага", "vat receivable"]):
                    vat_accounts[acc.name] = "Input"
        
        return vat_accounts
        
    except Exception:
        return {}


def _create_vat_adjustment(doc, vat_entries):
    """
    Create VAT adjustment records from Journal Entry.
    
    Args:
        doc: Journal Entry document
        vat_entries: List of VAT account entries
    """
    for entry in vat_entries:
        # Determine the adjustment amount
        # For Output VAT: Credit increases liability, Debit decreases
        # For Input VAT: Debit increases asset, Credit decreases
        if entry["vat_type"] == "Output":
            amount = flt(entry["credit"]) - flt(entry["debit"])
        else:  # Input
            amount = flt(entry["debit"]) - flt(entry["credit"])
        
        if not amount:
            continue
        
        # Create eTax Invoice Link for the adjustment
        link_doc = frappe.get_doc({
            "doctype": "eTax Invoice Link",
            "reference_doctype": "Journal Entry",
            "reference_name": doc.name,
            "company": doc.company,
            "posting_date": doc.posting_date,
            "vat_type": entry["vat_type"],
            "vat_amount": abs(amount),
            "taxable_amount": 0,  # Adjustments don't have taxable amount
            "total_amount": abs(amount),
            "vat_rate": 0,  # Rate not applicable for adjustments
            "is_adjustment": 1,
            "adjustment_type": "Increase" if amount > 0 else "Decrease",
            "remarks": doc.user_remark or doc.remark or f"VAT Adjustment via {doc.name}",
            "status": "Pending"
        })
        link_doc.insert(ignore_permissions=True)
    
    frappe.db.commit()


def _is_etax_vat_sync_enabled():
    """Check if eTax VAT sync is enabled."""
    try:
        return frappe.db.get_single_value("eTax Settings", "enable_erpnext_vat_sync") == 1
    except Exception:
        return False


def get_vat_adjustments(company: str, from_date: str, to_date: str) -> dict:
    """
    Get VAT adjustments from Journal Entries for a period.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        
    Returns:
        dict: VAT adjustments summary
    """
    adjustments = frappe.get_all(
        "eTax Invoice Link",
        filters={
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "reference_doctype": "Journal Entry",
            "is_adjustment": 1,
            "status": ["in", ["Pending", "Included"]]
        },
        fields=[
            "name",
            "reference_name",
            "vat_type",
            "vat_amount",
            "adjustment_type",
            "remarks",
            "posting_date"
        ],
        order_by="posting_date"
    )
    
    # Summarize by type
    output_increase = flt(0)
    output_decrease = flt(0)
    input_increase = flt(0)
    input_decrease = flt(0)
    
    for adj in adjustments:
        if adj.vat_type == "Output":
            if adj.adjustment_type == "Increase":
                output_increase += flt(adj.vat_amount)
            else:
                output_decrease += flt(adj.vat_amount)
        else:  # Input
            if adj.adjustment_type == "Increase":
                input_increase += flt(adj.vat_amount)
            else:
                input_decrease += flt(adj.vat_amount)
    
    return {
        "period": {"from_date": from_date, "to_date": to_date},
        "company": company,
        "adjustments": adjustments,
        "summary": {
            "output_vat": {
                "increases": flt(output_increase, 2),
                "decreases": flt(output_decrease, 2),
                "net": flt(output_increase - output_decrease, 2)
            },
            "input_vat": {
                "increases": flt(input_increase, 2),
                "decreases": flt(input_decrease, 2),
                "net": flt(input_increase - input_decrease, 2)
            }
        },
        "count": len(adjustments)
    }
