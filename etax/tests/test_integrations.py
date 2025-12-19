# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Integration Tests

Tests for the ERPNext integration hooks:
- Sales Invoice → eTax Invoice Link
- Purchase Invoice → eTax Invoice Link  
- Journal Entry → eTax VAT Adjustments

Uses FrappeTestCase for proper Frappe integration.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestETaxVATExtraction(FrappeTestCase):
    """Test suite for VAT extraction logic."""

    def test_sales_invoice_vat_extraction_with_vat(self):
        """Test VAT extraction from Sales Invoice with VAT."""
        from etax.integrations.sales_invoice import _extract_vat_from_invoice
        
        # Mock invoice document
        mock_invoice = MagicMock()
        mock_invoice.grand_total = 110000
        mock_invoice.net_total = 100000
        mock_invoice.taxes = [
            MagicMock(
                description="VAT 10%",
                account_head="VAT - TC",
                tax_amount=10000,
                rate=10
            )
        ]
        mock_invoice.get.return_value = None
        
        result = _extract_vat_from_invoice(mock_invoice)
        
        self.assertEqual(result["vat_amount"], 10000)
        self.assertEqual(result["vat_rate"], 10)
        self.assertEqual(result["total_amount"], 110000)

    def test_sales_invoice_vat_extraction_no_vat(self):
        """Test VAT extraction when no VAT is present."""
        from etax.integrations.sales_invoice import _extract_vat_from_invoice
        
        # Mock invoice without VAT
        mock_invoice = MagicMock()
        mock_invoice.grand_total = 100000
        mock_invoice.net_total = 100000
        mock_invoice.taxes = []
        mock_invoice.get.return_value = None
        
        result = _extract_vat_from_invoice(mock_invoice)
        
        self.assertEqual(result["vat_amount"], 0)
        self.assertEqual(result["taxable_amount"], 100000)

    def test_sales_invoice_mongolian_vat_keyword(self):
        """Test VAT extraction with Mongolian keyword НӨАТ."""
        from etax.integrations.sales_invoice import _extract_vat_from_invoice
        
        mock_invoice = MagicMock()
        mock_invoice.grand_total = 110000
        mock_invoice.net_total = 100000
        mock_invoice.taxes = [
            MagicMock(
                description="НӨАТ 10%",
                account_head="НӨАТ - TC",
                tax_amount=10000,
                rate=10
            )
        ]
        mock_invoice.get.return_value = None
        
        result = _extract_vat_from_invoice(mock_invoice)
        
        self.assertEqual(result["vat_amount"], 10000)

    def test_purchase_invoice_vat_extraction(self):
        """Test VAT extraction from Purchase Invoice."""
        from etax.integrations.purchase_invoice import _extract_vat_from_invoice
        
        mock_invoice = MagicMock()
        mock_invoice.grand_total = 55000
        mock_invoice.net_total = 50000
        mock_invoice.taxes = [
            MagicMock(
                description="Input VAT",
                account_head="Input VAT - TC",
                tax_amount=5000,
                rate=10
            )
        ]
        mock_invoice.get.return_value = None
        
        result = _extract_vat_from_invoice(mock_invoice)
        
        self.assertEqual(result["vat_amount"], 5000)
        self.assertEqual(result["vat_rate"], 10)


class TestETaxSettingsCheck(FrappeTestCase):
    """Test suite for eTax settings checks."""

    @patch("frappe.db.get_single_value")
    def test_etax_vat_sync_enabled(self, mock_get_single_value):
        """Test eTax VAT sync enabled check."""
        from etax.integrations.sales_invoice import _is_etax_vat_sync_enabled
        
        # Test enabled
        mock_get_single_value.return_value = 1
        self.assertTrue(_is_etax_vat_sync_enabled())
        
        # Test disabled
        mock_get_single_value.return_value = 0
        self.assertFalse(_is_etax_vat_sync_enabled())

    @patch("frappe.db.get_single_value")
    def test_etax_vat_sync_exception_handling(self, mock_get_single_value):
        """Test graceful handling when settings don't exist."""
        from etax.integrations.sales_invoice import _is_etax_vat_sync_enabled
        
        mock_get_single_value.side_effect = Exception("Settings not found")
        self.assertFalse(_is_etax_vat_sync_enabled())


class TestETaxJournalEntry(FrappeTestCase):
    """Test suite for Journal Entry VAT detection."""

    @patch("frappe.get_all")
    @patch("frappe.get_cached_doc")
    def test_vat_account_detection_from_settings(self, mock_get_cached_doc, mock_get_all):
        """Test VAT account detection from settings."""
        from etax.integrations.journal_entry import _get_vat_accounts
        
        mock_settings = MagicMock()
        mock_settings.vat_output_account = "Output VAT - TC"
        mock_settings.vat_input_account = "Input VAT - TC"
        
        mock_get_cached_doc.return_value = mock_settings
        
        result = _get_vat_accounts("_Test Company")
        
        self.assertIn("Output VAT - TC", result)
        self.assertEqual(result["Output VAT - TC"], "Output")
        self.assertIn("Input VAT - TC", result)
        self.assertEqual(result["Input VAT - TC"], "Input")

    @patch("frappe.get_all")
    @patch("frappe.get_cached_doc")
    def test_vat_account_detection_fallback(self, mock_get_cached_doc, mock_get_all):
        """Test VAT account detection fallback to pattern matching."""
        from etax.integrations.journal_entry import _get_vat_accounts
        
        # No settings configured
        mock_settings = MagicMock()
        mock_settings.vat_output_account = None
        mock_settings.vat_input_account = None
        
        mock_get_cached_doc.return_value = mock_settings
        
        # Use frappe._dict for attribute access
        mock_get_all.return_value = [
            frappe._dict(name="Output VAT Payable - TC", account_name="Output VAT Payable"),
            frappe._dict(name="Input VAT Receivable - TC", account_name="Input VAT Receivable"),
        ]
        
        result = _get_vat_accounts("_Test Company")
        
        self.assertIn("Output VAT Payable - TC", result)
        self.assertIn("Input VAT Receivable - TC", result)


class TestETaxInvoiceLink(FrappeTestCase):
    """Test suite for eTax Invoice Link functionality."""

    def test_vat_totals_calculation_logic(self):
        """Test VAT totals calculation logic."""
        # Test the calculation logic
        output_vat_data = {"vat": 50000, "taxable": 500000, "total": 550000, "count": 10}
        input_vat_data = {"vat": 25000, "taxable": 250000, "total": 275000, "count": 5}
        
        # Calculate net VAT (output - input)
        net_vat = output_vat_data["vat"] - input_vat_data["vat"]
        
        self.assertEqual(net_vat, 25000)
        self.assertEqual(output_vat_data["vat"], 50000)
        self.assertEqual(input_vat_data["vat"], 25000)

    def test_vat_type_classification(self):
        """Test VAT type classification logic."""
        vat_types = {
            "Sales Invoice": "Output",
            "Purchase Invoice": "Input",
            "Journal Entry": None  # Determined by account
        }
        
        self.assertEqual(vat_types["Sales Invoice"], "Output")
        self.assertEqual(vat_types["Purchase Invoice"], "Input")


class TestVATSummary(FrappeTestCase):
    """Test suite for VAT summary functions."""

    @patch("frappe.get_all")
    def test_output_vat_summary(self, mock_get_all):
        """Test get_vat_summary for output VAT."""
        from etax.integrations.sales_invoice import get_vat_summary
        
        mock_get_all.side_effect = [
            [{"total_vat": 50000, "total_taxable": 500000, "total_amount": 550000, "invoice_count": 10}],
            [],  # rate breakdown
            [{"total_vat": 0, "total_taxable": 0, "count": 0}]  # returns
        ]
        
        result = get_vat_summary("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertEqual(result["vat_type"], "Output")
        self.assertEqual(result["totals"]["vat_amount"], 50000)
        self.assertEqual(result["totals"]["invoice_count"], 10)

    @patch("frappe.get_all")
    def test_input_vat_summary(self, mock_get_all):
        """Test get_vat_summary for input VAT."""
        from etax.integrations.purchase_invoice import get_vat_summary
        
        mock_get_all.side_effect = [
            [{"total_vat": 25000, "total_taxable": 250000, "total_amount": 275000, "invoice_count": 5}],
            [],  # rate breakdown
            [{"total_vat": 0, "total_taxable": 0, "count": 0}],  # returns
            []  # by supplier
        ]
        
        result = get_vat_summary("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertEqual(result["vat_type"], "Input")
        self.assertEqual(result["totals"]["vat_amount"], 25000)


class TestVATAdjustments(FrappeTestCase):
    """Test suite for VAT adjustments from Journal Entries."""

    @patch("frappe.get_all")
    def test_vat_adjustments_summary(self, mock_get_all):
        """Test get_vat_adjustments function."""
        from etax.integrations.journal_entry import get_vat_adjustments
        
        # Use frappe._dict for attribute access (Frappe returns dicts with dot notation)
        mock_get_all.return_value = [
            frappe._dict(
                name="ETAX-LNK-00001",
                reference_name="JV-00001",
                vat_type="Output",
                vat_amount=5000,
                adjustment_type="Increase",
                remarks="VAT correction",
                posting_date="2024-01-15"
            ),
            frappe._dict(
                name="ETAX-LNK-00002",
                reference_name="JV-00002",
                vat_type="Input",
                vat_amount=2000,
                adjustment_type="Decrease",
                remarks="Input VAT reversal",
                posting_date="2024-01-20"
            )
        ]
        
        result = get_vat_adjustments("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["summary"]["output_vat"]["increases"], 5000)
        self.assertEqual(result["summary"]["input_vat"]["decreases"], 2000)
