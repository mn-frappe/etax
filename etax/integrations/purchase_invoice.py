# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Purchase Invoice Integration

Captures Input VAT (НӨАТ худалдан авалт) from Purchase Invoices for tax reporting.
Input VAT can be claimed as credit against Output VAT in VAT returns.
"""

import frappe
from frappe import _
from frappe.utils import flt


def on_submit(doc, method=None):
    """
    Handle Purchase Invoice submission - capture VAT data for eTax.
    
    Args:
        doc: Purchase Invoice document
        method: Event method name
    """
    if not _is_etax_vat_sync_enabled():
        return
    
    # Skip debit notes / returns
    if doc.is_return:
        _handle_return_invoice(doc)
        return
    
    # Skip zero-value invoices
    if flt(doc.grand_total) <= 0:
        return
    
    # Create or update eTax Invoice Link
    _create_invoice_link(doc, "Purchase Invoice")


def on_cancel(doc, method=None):
    """
    Handle Purchase Invoice cancellation.
    
    Args:
        doc: Purchase Invoice document
        method: Event method name
    """
    if not _is_etax_vat_sync_enabled():
        return
    
    # Mark linked eTax records as cancelled
    _cancel_invoice_link(doc.name, "Purchase Invoice")


def _handle_return_invoice(doc):
    """
    Handle debit notes / return invoices.
    
    Returns reduce VAT credit (input VAT) and need to be linked to original invoice.
    """
    if not doc.return_against:
        frappe.log_error(
            message=f"Return invoice {doc.name} has no return_against reference",
            title="eTax: Return Invoice Warning"
        )
        return
    
    # Create link for the return with negative amounts
    _create_invoice_link(doc, "Purchase Invoice", is_return=True)


def _create_invoice_link(doc, doctype, is_return=False):
    """
    Create eTax Invoice Link record.
    
    Args:
        doc: Invoice document
        doctype: DocType name
        is_return: Whether this is a return/debit note
    """
    # Calculate VAT amounts from invoice
    vat_data = _extract_vat_from_invoice(doc)
    
    if not vat_data.get("vat_amount"):
        # No VAT on this invoice
        return
    
    # Check if link already exists
    existing = frappe.db.exists(
        "eTax Invoice Link",
        {
            "reference_doctype": doctype,
            "reference_name": doc.name
        }
    )
    
    if existing:
        # Update existing link
        link_doc = frappe.get_doc("eTax Invoice Link", existing)
        link_doc.update({
            "vat_amount": vat_data["vat_amount"],
            "taxable_amount": vat_data["taxable_amount"],
            "total_amount": vat_data["total_amount"],
            "vat_rate": vat_data["vat_rate"],
            "status": "Pending"
        })
        link_doc.save(ignore_permissions=True)
    else:
        # Create new link
        link_doc = frappe.get_doc({
            "doctype": "eTax Invoice Link",
            "reference_doctype": doctype,
            "reference_name": doc.name,
            "company": doc.company,
            "posting_date": doc.posting_date,
            "supplier": doc.supplier,
            "supplier_tin": _get_supplier_tin(doc.supplier),
            "vat_type": "Input",  # Purchase = Input VAT
            "vat_amount": vat_data["vat_amount"] * (-1 if is_return else 1),
            "taxable_amount": vat_data["taxable_amount"] * (-1 if is_return else 1),
            "total_amount": vat_data["total_amount"] * (-1 if is_return else 1),
            "vat_rate": vat_data["vat_rate"],
            "is_return": is_return,
            "return_against": doc.return_against if is_return else None,
            "status": "Pending"
        })
        link_doc.insert(ignore_permissions=True)
    
    frappe.db.commit()


def _cancel_invoice_link(invoice_name, doctype):
    """
    Mark eTax Invoice Link as cancelled.
    
    Args:
        invoice_name: Name of the cancelled invoice
        doctype: DocType name
    """
    links = frappe.get_all(
        "eTax Invoice Link",
        filters={
            "reference_doctype": doctype,
            "reference_name": invoice_name,
            "status": ["!=", "Submitted"]
        },
        pluck="name"
    )
    
    for link_name in links:
        frappe.db.set_value(
            "eTax Invoice Link",
            link_name,
            "status",
            "Cancelled"
        )


def _extract_vat_from_invoice(doc):
    """
    Extract VAT information from Purchase Invoice.
    
    Mongolia standard VAT rate is 10%.
    
    Args:
        doc: Purchase Invoice document
        
    Returns:
        dict: VAT data with vat_amount, taxable_amount, total_amount, vat_rate
    """
    vat_amount = flt(0)
    vat_rate = flt(10)  # Default Mongolia VAT rate
    
    # Method 1: Check taxes table for VAT
    for tax in doc.taxes or []:
        tax_desc = (tax.description or "").lower()
        tax_type = (tax.account_head or "").lower()
        
        # Identify VAT taxes by common patterns
        if any(vat_keyword in tax_desc or vat_keyword in tax_type 
               for vat_keyword in ["vat", "нөат", "nuat", "value added", "input tax"]):
            vat_amount += flt(tax.tax_amount)
            
            # Extract rate if available
            if tax.rate:
                vat_rate = flt(tax.rate)
    
    # Method 2: If no VAT in taxes, check if inclusive pricing is used
    if not vat_amount and doc.get("taxes_and_charges"):
        try:
            # Get the tax template to check if VAT is included
            template = frappe.get_cached_doc("Purchase Taxes and Charges Template", doc.taxes_and_charges)
            for tax in template.taxes or []:
                if tax.included_in_print_rate and "vat" in (tax.description or "").lower():
                    # VAT is included in item prices
                    # Calculate: VAT = Total * rate / (100 + rate)
                    vat_rate = flt(tax.rate) or 10
                    vat_amount = flt(doc.grand_total) * vat_rate / (100 + vat_rate)
        except Exception:
            # Tax template may not exist or be inaccessible - continue with manual calculation
            pass
    
    # Calculate taxable amount
    if vat_amount:
        taxable_amount = flt(doc.net_total) if doc.net_total else flt(doc.grand_total) - vat_amount
    else:
        taxable_amount = flt(doc.grand_total)
    
    return {
        "vat_amount": flt(vat_amount, 2),
        "taxable_amount": flt(taxable_amount, 2),
        "total_amount": flt(doc.grand_total, 2),
        "vat_rate": vat_rate
    }


def _get_supplier_tin(supplier):
    """
    Get supplier TIN (Tax Identification Number).
    
    Args:
        supplier: Supplier name
        
    Returns:
        str: Supplier TIN or None
    """
    if not supplier:
        return None
    
    # Check custom field first
    tin = frappe.db.get_value("Supplier", supplier, "custom_tax_id")
    
    if not tin:
        # Fall back to standard tax_id field
        tin = frappe.db.get_value("Supplier", supplier, "tax_id")
    
    return tin


def _is_etax_vat_sync_enabled():
    """Check if eTax VAT sync is enabled."""
    try:
        return frappe.db.get_single_value("eTax Settings", "enable_erpnext_vat_sync") == 1
    except Exception:
        return False


def get_vat_summary(company: str, from_date: str, to_date: str) -> dict:
    """
    Get Purchase VAT (Input VAT) summary for eTax reporting.
    
    Used by eTax Declaration forms to pre-fill VAT credit data.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        
    Returns:
        dict: VAT summary with totals and breakdowns
    """
    # Get from eTax Invoice Links
    links = frappe.get_all(
        "eTax Invoice Link",
        filters={
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "vat_type": "Input",
            "status": ["in", ["Pending", "Included"]]
        },
        fields=[
            "sum(vat_amount) as total_vat",
            "sum(taxable_amount) as total_taxable",
            "sum(total_amount) as total_amount",
            "count(*) as invoice_count"
        ]
    )
    
    # Get breakdown by VAT rate
    rate_breakdown = frappe.get_all(
        "eTax Invoice Link",
        filters={
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "vat_type": "Input",
            "status": ["in", ["Pending", "Included"]]
        },
        fields=[
            "vat_rate",
            "sum(vat_amount) as vat_amount",
            "sum(taxable_amount) as taxable_amount",
            "count(*) as count"
        ],
        group_by="vat_rate"
    )
    
    # Get debit notes summary
    returns = frappe.get_all(
        "eTax Invoice Link",
        filters={
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "vat_type": "Input",
            "is_return": 1,
            "status": ["in", ["Pending", "Included"]]
        },
        fields=[
            "sum(vat_amount) as total_vat",
            "sum(taxable_amount) as total_taxable",
            "count(*) as count"
        ]
    )
    
    # Get by supplier for detailed reporting
    by_supplier = frappe.get_all(
        "eTax Invoice Link",
        filters={
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "vat_type": "Input",
            "status": ["in", ["Pending", "Included"]]
        },
        fields=[
            "supplier",
            "supplier_tin",
            "sum(vat_amount) as vat_amount",
            "sum(taxable_amount) as taxable_amount",
            "count(*) as invoice_count"
        ],
        group_by="supplier",
        order_by="vat_amount desc",
        limit=20
    )
    
    summary = links[0] if links else {}
    returns_summary = returns[0] if returns else {}
    
    return {
        "vat_type": "Input",
        "period": {"from_date": from_date, "to_date": to_date},
        "company": company,
        "totals": {
            "vat_amount": flt(summary.get("total_vat"), 2),
            "taxable_amount": flt(summary.get("total_taxable"), 2),
            "total_amount": flt(summary.get("total_amount"), 2),
            "invoice_count": summary.get("invoice_count") or 0
        },
        "by_rate": rate_breakdown,
        "by_supplier": by_supplier,
        "returns": {
            "vat_amount": flt(returns_summary.get("total_vat"), 2),
            "taxable_amount": flt(returns_summary.get("total_taxable"), 2),
            "count": returns_summary.get("count") or 0
        }
    }


def get_claimable_vat(company: str, from_date: str, to_date: str) -> dict:
    """
    Get claimable Input VAT for VAT return.
    
    Some Input VAT may not be claimable (e.g., entertainment expenses).
    This function returns the total claimable amount.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        
    Returns:
        dict: Claimable VAT data
    """
    summary = get_vat_summary(company, from_date, to_date)
    
    # For now, assume all Input VAT is claimable
    # In future, could add logic to exclude non-claimable items
    return {
        "claimable_vat": summary["totals"]["vat_amount"],
        "non_claimable_vat": 0,
        "total_input_vat": summary["totals"]["vat_amount"]
    }
