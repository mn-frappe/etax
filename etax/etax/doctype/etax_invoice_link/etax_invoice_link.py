# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Invoice Link DocType

Links ERPNext invoices (Sales Invoice, Purchase Invoice, Journal Entry)
to eTax tax declarations for VAT reporting.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class eTaxInvoiceLink(Document):
    """eTax Invoice Link - tracks which invoices are included in tax declarations."""
    
    def validate(self):
        """Validate the document."""
        self.validate_reference()
        self.validate_amounts()
        self.set_party_details()
    
    def validate_reference(self):
        """Validate that the reference document exists."""
        if self.reference_doctype and self.reference_name:
            if not frappe.db.exists(self.reference_doctype, self.reference_name):
                frappe.throw(
                    _("Reference {0} {1} does not exist").format(
                        self.reference_doctype, self.reference_name
                    )
                )
    
    def validate_amounts(self):
        """Validate VAT amounts."""
        if flt(self.vat_amount) < 0 and not self.is_return:
            frappe.throw(_("VAT Amount cannot be negative for non-return invoices"))
    
    def set_party_details(self):
        """Auto-set party details from reference document."""
        if not self.reference_doctype or not self.reference_name:
            return
        
        doc = frappe.get_doc(self.reference_doctype, self.reference_name)
        
        if self.reference_doctype == "Sales Invoice":
            if not self.customer:
                self.customer = doc.customer
            if not self.customer_tin:
                self.customer_tin = frappe.db.get_value(
                    "Customer", doc.customer, "custom_tax_id"
                ) or frappe.db.get_value("Customer", doc.customer, "tax_id")
        
        elif self.reference_doctype == "Purchase Invoice":
            if not self.supplier:
                self.supplier = doc.supplier
            if not self.supplier_tin:
                self.supplier_tin = frappe.db.get_value(
                    "Supplier", doc.supplier, "custom_tax_id"
                ) or frappe.db.get_value("Supplier", doc.supplier, "tax_id")
    
    def include_in_declaration(self, declaration_name: str):
        """
        Mark this link as included in a tax declaration.
        
        Args:
            declaration_name: Name of the eTax Report
        """
        self.status = "Included"
        self.etax_declaration = declaration_name
        self.included_date = now_datetime()
        self.save(ignore_permissions=True)
    
    def mark_submitted(self):
        """Mark as submitted to tax authority."""
        if self.status != "Included":
            frappe.throw(_("Only Included records can be marked as Submitted"))
        self.status = "Submitted"
        self.save(ignore_permissions=True)
    
    def unlink_from_declaration(self):
        """Remove from declaration (for corrections)."""
        if self.status == "Submitted":
            frappe.throw(_("Cannot unlink submitted records"))
        
        self.status = "Pending"
        self.etax_declaration = None
        self.included_date = None
        self.save(ignore_permissions=True)


@frappe.whitelist()
def get_pending_links(company: str, vat_type: str, from_date: str, to_date: str):
    """
    Get pending invoice links for inclusion in declaration.
    
    Args:
        company: Company name
        vat_type: "Output" or "Input"
        from_date: Period start
        to_date: Period end
        
    Returns:
        list: Pending invoice links
    """
    return frappe.get_all(
        "eTax Invoice Link",
        filters={
            "company": company,
            "vat_type": vat_type,
            "posting_date": ["between", [from_date, to_date]],
            "status": "Pending"
        },
        fields=[
            "name", "reference_doctype", "reference_name",
            "posting_date", "vat_amount", "taxable_amount",
            "total_amount", "customer", "supplier",
            "customer_tin", "supplier_tin", "is_return"
        ],
        order_by="posting_date"
    )


@frappe.whitelist()
def bulk_include_in_declaration(links: list, declaration_name: str):
    """
    Bulk include multiple links in a declaration.
    
    Args:
        links: List of eTax Invoice Link names
        declaration_name: eTax Report name
        
    Returns:
        dict: Result with count
    """
    if isinstance(links, str):
        import json
        links = json.loads(links)
    
    count = 0
    for link_name in links:
        doc = frappe.get_doc("eTax Invoice Link", link_name)
        doc.include_in_declaration(declaration_name)
        count += 1
    
    frappe.db.commit()
    
    return {"success": True, "count": count}


@frappe.whitelist()
def get_vat_totals(company: str, from_date: str, to_date: str):
    """
    Get VAT totals for a period.
    
    Args:
        company: Company name
        from_date: Period start
        to_date: Period end
        
    Returns:
        dict: Output and Input VAT totals
    """
    output_vat = frappe.db.sql("""
        SELECT 
            SUM(vat_amount) as vat,
            SUM(taxable_amount) as taxable,
            SUM(total_amount) as total,
            COUNT(*) as count
        FROM `tabeTax Invoice Link`
        WHERE company = %s
            AND posting_date BETWEEN %s AND %s
            AND vat_type = 'Output'
            AND status IN ('Pending', 'Included')
    """, (company, from_date, to_date), as_dict=True)[0]
    
    input_vat = frappe.db.sql("""
        SELECT 
            SUM(vat_amount) as vat,
            SUM(taxable_amount) as taxable,
            SUM(total_amount) as total,
            COUNT(*) as count
        FROM `tabeTax Invoice Link`
        WHERE company = %s
            AND posting_date BETWEEN %s AND %s
            AND vat_type = 'Input'
            AND status IN ('Pending', 'Included')
    """, (company, from_date, to_date), as_dict=True)[0]
    
    return {
        "output_vat": {
            "vat_amount": flt(output_vat.get("vat"), 2),
            "taxable_amount": flt(output_vat.get("taxable"), 2),
            "total_amount": flt(output_vat.get("total"), 2),
            "count": output_vat.get("count") or 0
        },
        "input_vat": {
            "vat_amount": flt(input_vat.get("vat"), 2),
            "taxable_amount": flt(input_vat.get("taxable"), 2),
            "total_amount": flt(input_vat.get("total"), 2),
            "count": input_vat.get("count") or 0
        },
        "net_vat": flt(output_vat.get("vat"), 2) - flt(input_vat.get("vat"), 2)
    }
