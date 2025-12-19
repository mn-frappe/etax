# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax ERPNext Integrations

Automatically captures VAT data from ERPNext transactions:
- Sales Invoice: Output VAT (НӨАТ борлуулалт)
- Purchase Invoice: Input VAT (НӨАТ худалдан авалт)
- Journal Entry: VAT adjustments and corrections

All integrations respect the "Enable ERPNext VAT Sync" setting in eTax Settings.
"""

from etax.integrations.sales_invoice import (
    on_submit as sales_invoice_on_submit,
    on_cancel as sales_invoice_on_cancel,
    get_vat_summary as get_sales_vat_summary,
)
from etax.integrations.purchase_invoice import (
    on_submit as purchase_invoice_on_submit,
    on_cancel as purchase_invoice_on_cancel,
    get_vat_summary as get_purchase_vat_summary,
)
from etax.integrations.journal_entry import (
    on_submit as journal_entry_on_submit,
    on_cancel as journal_entry_on_cancel,
    get_vat_adjustments,
)

__all__ = [
    # Sales Invoice
    "sales_invoice_on_submit",
    "sales_invoice_on_cancel",
    "get_sales_vat_summary",
    # Purchase Invoice
    "purchase_invoice_on_submit",
    "purchase_invoice_on_cancel",
    "get_purchase_vat_summary",
    # Journal Entry
    "journal_entry_on_submit",
    "journal_entry_on_cancel",
    "get_vat_adjustments",
]
