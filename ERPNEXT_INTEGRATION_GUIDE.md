# ERPNext Integration Guide for Mongolian Government Apps

## Overview

This guide explains how to integrate the 4 Mongolian government apps (eTax, eBarimt, eBalance, QPay) with Frappe/ERPNext.

---

## 1. Integration Architecture

### 1.1 Three Integration Levels

```
┌─────────────────────────────────────────────────────────────────┐
│                     ERPNext Integration Levels                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 1: Custom Fields                                         │
│  ├── Add fields to existing DocTypes (Customer, Item, etc.)     │
│  └── Store MN-specific data (TIN, registry number, etc.)        │
│                                                                 │
│  Level 2: Document Events (Hooks)                               │
│  ├── Trigger actions on document lifecycle                      │
│  └── Auto-submit receipts, sync data, validate                  │
│                                                                 │
│  Level 3: API Methods                                           │
│  ├── Expose functions via @frappe.whitelist()                   │
│  └── Call from client-side JS or external systems               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Custom Fields Setup

### 2.1 Define Custom Fields in Python

Create `your_app/integrations/custom_fields.py`:

```python
def get_custom_fields():
    """Return custom fields to be created during installation"""
    return {
        "Customer": [
            {
                "fieldname": "custom_tin",
                "label": "TIN (ТИН)",
                "fieldtype": "Data",
                "insert_after": "tax_id",
                "description": "Taxpayer Identification Number"
            },
            {
                "fieldname": "custom_regno",
                "label": "Registration No (РД)",
                "fieldtype": "Data",
                "insert_after": "custom_tin"
            },
            {
                "fieldname": "custom_vat_payer",
                "label": "VAT Payer",
                "fieldtype": "Check",
                "insert_after": "custom_regno",
                "read_only": 1
            }
        ],
        "Sales Invoice": [
            {
                "fieldname": "custom_ebarimt_receipt_id",
                "label": "eBarimt Receipt ID",
                "fieldtype": "Data",
                "insert_after": "remarks",
                "read_only": 1
            },
            {
                "fieldname": "custom_ebarimt_lottery",
                "label": "Lottery Number",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_receipt_id",
                "read_only": 1
            }
        ],
        "Item": [
            {
                "fieldname": "custom_ebarimt_product_code",
                "label": "eBarimt Product Code",
                "fieldtype": "Link",
                "options": "eBarimt Product Code",
                "insert_after": "barcodes"
            }
        ],
        "Company": [
            {
                "fieldname": "custom_merchant_tin",
                "label": "Merchant TIN",
                "fieldtype": "Data",
                "insert_after": "tax_id"
            },
            {
                "fieldname": "custom_pos_no",
                "label": "POS Number",
                "fieldtype": "Data",
                "insert_after": "custom_merchant_tin"
            }
        ]
    }
```

### 2.2 Install Custom Fields

In `your_app/install.py`:

```python
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Run after app installation"""
    from your_app.integrations.custom_fields import get_custom_fields
    
    custom_fields = get_custom_fields()
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
```

---

## 3. Document Events (Hooks)

### 3.1 Configure hooks.py

```python
# hooks.py

app_name = "your_app"
app_title = "Your App"

# Required Apps
required_apps = ["frappe", "erpnext"]

# Document Events - trigger on document lifecycle
doc_events = {
    "Sales Invoice": {
        "validate": "your_app.integrations.sales_invoice.validate_invoice",
        "on_submit": "your_app.integrations.sales_invoice.on_submit_invoice",
        "on_cancel": "your_app.integrations.sales_invoice.on_cancel_invoice"
    },
    "Customer": {
        "validate": "your_app.integrations.customer.validate_customer",
        "after_insert": "your_app.integrations.customer.after_insert_customer"
    },
    "Payment Entry": {
        "on_submit": "your_app.integrations.payment_entry.on_submit_payment"
    }
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "your_app.tasks.sync_daily"
    ],
    "hourly": [
        "your_app.tasks.process_pending"
    ]
}

# Installation hooks
after_install = "your_app.install.after_install"
after_migrate = "your_app.install.after_migrate"
```

### 3.2 Implement Document Event Handlers

Create `your_app/integrations/sales_invoice.py`:

```python
import frappe
from frappe import _

def validate_invoice(doc, method=None):
    """Validate invoice before save"""
    # Check if integration is enabled
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    # Validate customer TIN for B2B
    if doc.get("custom_ebarimt_bill_type") == "B2B_RECEIPT":
        customer_tin = frappe.db.get_value("Customer", doc.customer, "custom_tin")
        if not customer_tin:
            frappe.throw(_("Customer TIN required for B2B receipts"))


def on_submit_invoice(doc, method=None):
    """Auto-submit eBarimt receipt on invoice submission"""
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    if not settings.enabled or not settings.auto_submit_on_invoice:
        return
    
    # Skip if already has receipt
    if doc.get("custom_ebarimt_receipt_id"):
        return
    
    # Submit receipt
    try:
        result = submit_ebarimt_receipt(doc)
        
        if result.get("success"):
            # Update invoice with receipt info
            frappe.db.set_value("Sales Invoice", doc.name, {
                "custom_ebarimt_receipt_id": result.get("billId"),
                "custom_ebarimt_lottery": result.get("lottery")
            }, update_modified=False)
            
            frappe.msgprint(
                _("eBarimt receipt created. Lottery: {0}").format(result.get("lottery")),
                indicator="green"
            )
    except Exception as e:
        frappe.log_error(message=str(e), title=f"eBarimt Failed: {doc.name}")
        frappe.msgprint(_("eBarimt submission failed: {0}").format(str(e)), indicator="red")


def on_cancel_invoice(doc, method=None):
    """Void eBarimt receipt on invoice cancellation"""
    if not doc.get("custom_ebarimt_receipt_id"):
        return
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    if not settings.auto_void_on_cancel:
        return
    
    try:
        void_ebarimt_receipt(doc.custom_ebarimt_receipt_id)
        frappe.msgprint(_("eBarimt receipt voided"), indicator="orange")
    except Exception as e:
        frappe.log_error(message=str(e), title=f"eBarimt Void Failed: {doc.name}")


def submit_ebarimt_receipt(invoice_doc):
    """Submit receipt to eBarimt API"""
    from ebarimt.api.client import EBarimtClient
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    client = EBarimtClient(settings)
    
    # Build receipt data from invoice
    receipt_data = {
        "amount": invoice_doc.grand_total,
        "vat": invoice_doc.total_taxes_and_charges,
        "billType": invoice_doc.get("custom_ebarimt_bill_type") or "B2C_RECEIPT",
        "districtCode": settings.district_code,
        "stocks": []
    }
    
    # Add line items
    for item in invoice_doc.items:
        receipt_data["stocks"].append({
            "code": item.item_code,
            "name": item.item_name,
            "qty": item.qty,
            "unitPrice": item.rate,
            "totalAmount": item.amount
        })
    
    return client.create_receipt(receipt_data)
```

---

## 4. Client-Side Integration (JavaScript)

### 4.1 Add DocType JS

In `hooks.py`:

```python
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "Customer": "public/js/customer.js"
}
```

### 4.2 Create Client-Side Script

Create `your_app/public/js/sales_invoice.js`:

```javascript
frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        // Add custom buttons
        if (frm.doc.docstatus === 1 && !frm.doc.custom_ebarimt_receipt_id) {
            frm.add_custom_button(__('Submit eBarimt'), function() {
                submit_ebarimt(frm);
            }, __('eBarimt'));
        }
        
        // Show lottery if exists
        if (frm.doc.custom_ebarimt_lottery) {
            frm.dashboard.add_indicator(
                __('Lottery: {0}', [frm.doc.custom_ebarimt_lottery]),
                'green'
            );
        }
    },
    
    customer: function(frm) {
        // Auto-fetch customer TIN info
        if (frm.doc.customer) {
            frappe.db.get_value('Customer', frm.doc.customer, 
                ['custom_tin', 'custom_vat_payer'], (r) => {
                    if (r && r.custom_tin) {
                        // Set bill type based on customer
                        frm.set_value('custom_ebarimt_bill_type', 
                            r.custom_vat_payer ? 'B2B_RECEIPT' : 'B2C_RECEIPT'
                        );
                    }
                }
            );
        }
    }
});

function submit_ebarimt(frm) {
    frappe.call({
        method: 'ebarimt.api.api.submit_receipt',
        args: {
            doctype: 'Sales Invoice',
            docname: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Submitting eBarimt receipt...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('Receipt created! Lottery: {0}', [r.message.lottery]),
                    indicator: 'green'
                });
                frm.reload_doc();
            }
        }
    });
}
```

### 4.3 Customer Lookup Script

Create `your_app/public/js/customer.js`:

```javascript
frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        // Add TIN lookup button
        if (!frm.is_new()) {
            frm.add_custom_button(__('Lookup TIN'), function() {
                lookup_taxpayer(frm);
            }, __('eBarimt'));
        }
    },
    
    custom_regno: function(frm) {
        // Auto-lookup when registry number entered
        if (frm.doc.custom_regno && frm.doc.custom_regno.length >= 7) {
            lookup_tin_from_regno(frm);
        }
    }
});

function lookup_taxpayer(frm) {
    if (!frm.doc.custom_tin) {
        frappe.msgprint(__('Please enter TIN first'));
        return;
    }
    
    frappe.call({
        method: 'ebarimt.api.api.get_taxpayer_info',
        args: { tin: frm.doc.custom_tin },
        callback: function(r) {
            if (r.message && r.message.found) {
                frm.set_value('custom_taxpayer_name', r.message.name);
                frm.set_value('custom_vat_payer', r.message.vatPayer ? 1 : 0);
                frm.set_value('custom_city_payer', r.message.cityPayer ? 1 : 0);
                frm.set_value('custom_taxpayer_synced', 1);
                
                frappe.show_alert({
                    message: __('Taxpayer info updated'),
                    indicator: 'green'
                });
            } else {
                frappe.show_alert({
                    message: __('Taxpayer not found'),
                    indicator: 'red'
                });
            }
        }
    });
}

function lookup_tin_from_regno(frm) {
    frappe.call({
        method: 'ebarimt.api.api.get_tin_from_regno',
        args: { regno: frm.doc.custom_regno },
        callback: function(r) {
            if (r.message) {
                frm.set_value('custom_tin', r.message);
                // Then lookup full taxpayer info
                lookup_taxpayer(frm);
            }
        }
    });
}
```

---

## 5. API Methods

### 5.1 Expose Functions via Whitelist

Create `your_app/api/api.py`:

```python
import frappe
from frappe import _

@frappe.whitelist()
def get_taxpayer_info(tin):
    """
    Get taxpayer information from eBarimt
    
    Args:
        tin: Taxpayer Identification Number
        
    Returns:
        dict: Taxpayer info (name, vatPayer, cityPayer)
    """
    from ebarimt.api.client import EBarimtClient
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    client = EBarimtClient(settings)
    
    return client.get_taxpayer_info(tin)


@frappe.whitelist()
def get_tin_from_regno(regno):
    """
    Get TIN from registry number
    
    Args:
        regno: Company registration number
        
    Returns:
        str: TIN number
    """
    from ebarimt.api.client import EBarimtClient
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    client = EBarimtClient(settings)
    
    return client.get_tin_by_regno(regno)


@frappe.whitelist()
def submit_receipt(doctype, docname):
    """
    Submit eBarimt receipt for a document
    
    Args:
        doctype: Document type (Sales Invoice, POS Invoice)
        docname: Document name
        
    Returns:
        dict: Receipt result with billId, lottery, qrData
    """
    frappe.has_permission(doctype, "write", throw=True)
    
    doc = frappe.get_doc(doctype, docname)
    
    if doc.docstatus != 1:
        frappe.throw(_("Document must be submitted first"))
    
    if doc.get("custom_ebarimt_receipt_id"):
        frappe.throw(_("Receipt already exists for this document"))
    
    from your_app.integrations.sales_invoice import submit_ebarimt_receipt
    
    result = submit_ebarimt_receipt(doc)
    
    if result.get("success"):
        frappe.db.set_value(doctype, docname, {
            "custom_ebarimt_receipt_id": result.get("billId"),
            "custom_ebarimt_lottery": result.get("lottery")
        }, update_modified=False)
        frappe.db.commit()
    
    return result


@frappe.whitelist()
def void_receipt(doctype, docname):
    """Void eBarimt receipt"""
    frappe.has_permission(doctype, "write", throw=True)
    
    doc = frappe.get_doc(doctype, docname)
    
    if not doc.get("custom_ebarimt_receipt_id"):
        frappe.throw(_("No receipt to void"))
    
    from ebarimt.api.client import EBarimtClient
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    client = EBarimtClient(settings)
    
    result = client.void_receipt(doc.custom_ebarimt_receipt_id)
    
    if result.get("success"):
        frappe.db.set_value(doctype, docname, {
            "custom_ebarimt_receipt_id": None,
            "custom_ebarimt_lottery": None
        }, update_modified=False)
        frappe.db.commit()
    
    return result
```

---

## 6. Settings DocType

### 6.1 Create Settings DocType

Create `your_app/your_app/doctype/your_settings/your_settings.json`:

```json
{
    "doctype": "DocType",
    "name": "Your Settings",
    "module": "Your App",
    "issingle": 1,
    "fields": [
        {
            "fieldname": "enabled",
            "fieldtype": "Check",
            "label": "Enable Integration"
        },
        {
            "fieldname": "environment",
            "fieldtype": "Select",
            "label": "Environment",
            "options": "Staging\nProduction",
            "reqd": 1
        },
        {
            "fieldname": "username",
            "fieldtype": "Data",
            "label": "Username"
        },
        {
            "fieldname": "password",
            "fieldtype": "Password",
            "label": "Password"
        },
        {
            "fieldname": "org_regno",
            "fieldtype": "Data",
            "label": "Organization Registry No"
        },
        {
            "fieldname": "auto_submit_on_invoice",
            "fieldtype": "Check",
            "label": "Auto Submit on Invoice"
        }
    ]
}
```

### 6.2 Settings Controller

Create `your_app/your_app/doctype/your_settings/your_settings.py`:

```python
import frappe
from frappe.model.document import Document

class YourSettings(Document):
    def validate(self):
        if self.enabled and not self.username:
            frappe.throw("Username is required when integration is enabled")
    
    @frappe.whitelist()
    def test_connection(self):
        """Test API connection"""
        from your_app.api.client import YourClient
        
        try:
            client = YourClient(self)
            result = client.test_connection()
            
            if result.get("success"):
                self.db_set("connection_status", "Connected")
                return {"success": True, "message": "Connection successful"}
            else:
                self.db_set("connection_status", "Failed")
                return {"success": False, "message": result.get("message")}
        except Exception as e:
            self.db_set("connection_status", "Failed")
            return {"success": False, "message": str(e)}
```

---

## 7. Background Jobs

### 7.1 Scheduled Tasks

Create `your_app/tasks.py`:

```python
import frappe

def sync_daily():
    """Daily sync task"""
    if not frappe.db.get_single_value("Your Settings", "enabled"):
        return
    
    # Sync pending items
    sync_pending_receipts()
    
    # Cleanup old logs
    cleanup_old_logs()


def sync_pending_receipts():
    """Retry failed receipt submissions"""
    pending = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "custom_ebarimt_receipt_id": ["is", "not set"],
            "posting_date": [">=", frappe.utils.add_days(frappe.utils.today(), -7)]
        },
        limit=50
    )
    
    for inv in pending:
        try:
            doc = frappe.get_doc("Sales Invoice", inv.name)
            submit_ebarimt_receipt(doc)
        except Exception as e:
            frappe.log_error(message=str(e), title=f"Retry Failed: {inv.name}")


def cleanup_old_logs():
    """Delete old error logs"""
    retention_days = frappe.db.get_single_value("Your Settings", "log_retention_days") or 30
    
    frappe.db.delete(
        "Error Log",
        filters={
            "creation": ["<", frappe.utils.add_days(frappe.utils.today(), -retention_days)],
            "method": ["like", "%your_app%"]
        }
    )
```

### 7.2 Enqueue Long-Running Tasks

```python
import frappe

def process_large_batch(items):
    """Process items in background"""
    for item in items:
        frappe.enqueue(
            "your_app.tasks.process_single_item",
            queue="long",
            item_name=item.name,
            timeout=300
        )


def process_single_item(item_name):
    """Process single item (runs in background)"""
    doc = frappe.get_doc("Your DocType", item_name)
    # ... processing logic
    doc.save()
    frappe.db.commit()
```

---

## 8. Complete Integration Flow

### 8.1 eBarimt + Sales Invoice Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    Sales Invoice Workflow                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. User creates Sales Invoice                                 │
│     └── validate hook: check customer TIN for B2B              │
│                                                                │
│  2. User submits Sales Invoice                                 │
│     └── on_submit hook triggered                               │
│         ├── Check if eBarimt enabled                           │
│         ├── Check if auto_submit_on_invoice                    │
│         ├── Build receipt data from invoice                    │
│         ├── Call eBarimt API                                   │
│         └── Store receipt_id, lottery in custom fields         │
│                                                                │
│  3. If user cancels invoice                                    │
│     └── on_cancel hook triggered                               │
│         ├── Check if receipt exists                            │
│         ├── Void receipt via API                               │
│         └── Clear custom fields                                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 8.2 QPay + Payment Entry Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    QPay Payment Workflow                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. Create QPay Invoice linked to Sales Invoice                │
│     └── Generate QR code, deep links                           │
│                                                                │
│  2. Customer pays via bank app                                 │
│                                                                │
│  3. QPay sends callback to your server                         │
│     └── /api/method/qpay.api.callback                          │
│         ├── Verify payment                                     │
│         ├── Update QPay Invoice status                         │
│         ├── Create Payment Entry (if enabled)                  │
│         └── Create eBarimt via QPay API (if enabled)           │
│                                                                │
│  4. Payment Entry created                                      │
│     └── on_submit hook                                         │
│         └── Reconcile with Sales Invoice                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 9. Best Practices

### 9.1 Use Cached Documents

```python
# Good - uses cache
settings = frappe.get_cached_doc("eBarimt Settings")

# Bad - hits database every time
settings = frappe.get_doc("eBarimt Settings", "eBarimt Settings")
```

### 9.2 Handle Errors Gracefully

```python
def on_submit_invoice(doc, method=None):
    try:
        result = submit_receipt(doc)
    except Exception as e:
        # Log error but don't block invoice submission
        frappe.log_error(message=str(e), title=f"eBarimt Failed: {doc.name}")
        frappe.msgprint(
            _("eBarimt submission failed. You can retry later."),
            indicator="orange"
        )
        # Don't raise - let invoice submit succeed
```

### 9.3 Use Background Jobs for Slow Operations

```python
def after_insert_customer(doc, method=None):
    # Don't block - enqueue for background processing
    frappe.enqueue(
        "your_app.integrations.customer.sync_taxpayer_info",
        queue="short",
        customer_name=doc.name
    )
```

### 9.4 Update Without Triggering Hooks

```python
# Good - doesn't trigger validate/on_update
frappe.db.set_value("Sales Invoice", doc.name, {
    "custom_ebarimt_receipt_id": receipt_id,
    "custom_ebarimt_lottery": lottery
}, update_modified=False)

# Bad - triggers all hooks again
doc.custom_ebarimt_receipt_id = receipt_id
doc.save()
```

### 9.5 Check Permissions

```python
@frappe.whitelist()
def sensitive_action(doctype, docname):
    # Always check permissions for whitelisted methods
    frappe.has_permission(doctype, "write", throw=True)
    
    doc = frappe.get_doc(doctype, docname)
    # ... proceed with action
```

---

## 10. Testing Integration

### 10.1 Unit Tests

Create `your_app/tests/test_integration.py`:

```python
import frappe
import unittest

class TestEBarimtIntegration(unittest.TestCase):
    def setUp(self):
        # Enable test mode
        frappe.db.set_single_value("eBarimt Settings", "environment", "Staging")
        frappe.db.set_single_value("eBarimt Settings", "enabled", 1)
    
    def test_customer_tin_validation(self):
        """Test TIN format validation"""
        customer = frappe.new_doc("Customer")
        customer.customer_name = "Test Customer"
        customer.custom_tin = "invalid"
        
        self.assertRaises(frappe.ValidationError, customer.save)
    
    def test_receipt_submission(self):
        """Test eBarimt receipt submission"""
        # Create test invoice
        invoice = create_test_invoice()
        invoice.submit()
        
        # Check receipt was created
        invoice.reload()
        self.assertIsNotNone(invoice.custom_ebarimt_receipt_id)
        self.assertIsNotNone(invoice.custom_ebarimt_lottery)
    
    def tearDown(self):
        frappe.db.rollback()
```

### 10.2 Run Tests

```bash
cd /opt/bench
bench --site test.frappe.mn run-tests --app your_app
```

---

## Summary

| Integration Point | File | Purpose |
|-------------------|------|---------|
| Custom Fields | `integrations/custom_fields.py` | Add fields to ERPNext DocTypes |
| Document Events | `hooks.py` → `integrations/*.py` | Trigger on save/submit/cancel |
| Client JS | `public/js/*.js` | UI buttons, auto-fill |
| API Methods | `api/api.py` | Expose functions for JS calls |
| Settings | `doctype/your_settings/` | Store configuration |
| Background Jobs | `tasks.py` | Scheduled/async processing |
