# Financial Transaction Consolidation Strategy

## The Problem: Duplicate Transactions

When multiple apps are installed, the same business transaction can create **duplicate records**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DUPLICATE TRANSACTION SCENARIOS                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Scenario 1: DUPLICATE eBarimt RECEIPTS                                     │
│  ─────────────────────────────────────────                                  │
│  Sales Invoice submitted                                                    │
│      ↓                                                                      │
│      ├── QPay Invoice created → Payment received → QPay creates eBarimt     │
│      │                                              (via ebarimt_v3/create) │
│      │                                                                      │
│      └── eBarimt app auto-submits receipt ← DUPLICATE!                      │
│          (via /rest/receipt)                                                │
│                                                                             │
│  Result: 2 eBarimt receipts for same invoice = TAX VIOLATION                │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Scenario 2: DUPLICATE PAYMENT ENTRIES                                      │
│  ─────────────────────────────────────────                                  │
│  Customer pays via QPay                                                     │
│      ↓                                                                      │
│      ├── QPay callback → Auto-creates Payment Entry                         │
│      │                                                                      │
│      └── Accountant manually creates Payment Entry ← DUPLICATE!             │
│                                                                             │
│  Result: 2 Payment Entries = Double accounting                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Scenario 3: INCONSISTENT TAX REPORTING                                     │
│  ─────────────────────────────────────────                                  │
│  Quarter end reporting                                                      │
│      ↓                                                                      │
│      ├── eTax: Reports from MTA tax returns                                 │
│      ├── eBalance: Financial statements to MOF                              │
│      └── eBarimt: VAT receipts issued                                       │
│                                                                             │
│  If not reconciled: VAT in eTax ≠ VAT in eBarimt = AUDIT RISK               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Solution: Single Source of Truth Architecture

### Core Principle: ERPNext Documents are MASTER

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSACTION HIERARCHY                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LEVEL 1: ERPNext Master Documents (Source of Truth)                        │
│  ════════════════════════════════════════════════════                       │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Sales     │  │  Purchase   │  │   Payment   │  │   Journal   │        │
│  │   Invoice   │  │   Invoice   │  │    Entry    │  │    Entry    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         │                │                │                │                │
│  LEVEL 2: App Transaction Logs (References to Master)                       │
│  ═══════════════════════════════════════════════════                        │
│         │                │                │                │                │
│         ▼                ▼                ▼                ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   eBarimt   │  │    eTax     │  │    QPay     │  │  eBalance   │        │
│  │ Receipt Log │  │   Report    │  │   Invoice   │  │   Report    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
│  RULE: App logs REFERENCE master docs, never duplicate data                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Transaction Flow Design

### Flow 1: Sales with QPay Payment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SALES + QPAY PAYMENT FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step 1: Sales Invoice Created                                              │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ Sales Invoice: INV-2024-001                                 │            │
│  │ ├─ customer: "ABC Company"                                  │            │
│  │ ├─ grand_total: 1,000,000                                   │            │
│  │ ├─ custom_ebarimt_bill_type: "B2B_RECEIPT"                  │            │
│  │ └─ custom_ebarimt_receipt_id: (empty - not yet submitted)   │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                          │                                                  │
│                          ▼                                                  │
│  Step 2: QPay Invoice Created (linked to Sales Invoice)                     │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ QPay Invoice: QPAY-2024-001                                 │            │
│  │ ├─ reference_doctype: "Sales Invoice"                       │            │
│  │ ├─ reference_name: "INV-2024-001"  ← LINK TO MASTER         │            │
│  │ ├─ amount: 1,000,000                                        │            │
│  │ ├─ status: "Pending"                                        │            │
│  │ ├─ qpay_invoice_id: "uuid-from-qpay"                        │            │
│  │ └─ ebarimt_created: 0                                       │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                          │                                                  │
│                          ▼                                                  │
│  Step 3: Customer Pays via Bank App                                         │
│                          │                                                  │
│                          ▼                                                  │
│  Step 4: QPay Callback Received                                             │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ QPay Callback Handler:                                      │            │
│  │ 1. Update QPay Invoice status = "Paid"                      │            │
│  │ 2. Create Payment Entry (if auto_create_payment_entry)      │            │
│  │ 3. Create eBarimt via QPay API (if ebarimt_enabled)         │            │
│  │ 4. Update Sales Invoice custom fields                       │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                          │                                                  │
│                          ▼                                                  │
│  Step 5: Payment Entry Created (ONE ONLY)                                   │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ Payment Entry: PE-2024-001                                  │            │
│  │ ├─ payment_type: "Receive"                                  │            │
│  │ ├─ party: "ABC Company"                                     │            │
│  │ ├─ paid_amount: 1,000,000                                   │            │
│  │ ├─ reference: Sales Invoice INV-2024-001                    │            │
│  │ ├─ custom_qpay_invoice: "QPAY-2024-001"  ← BACK-LINK        │            │
│  │ └─ custom_qpay_payment_id: "payment-uuid"                   │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                          │                                                  │
│                          ▼                                                  │
│  Step 6: eBarimt Created via QPay (ONE ONLY)                                │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ QPay Invoice Updated:                                       │            │
│  │ ├─ ebarimt_created: 1                                       │            │
│  │ ├─ ebarimt_id: "ebarimt-uuid"                               │            │
│  │ └─ ebarimt_lottery: "АА12345678"                            │            │
│  │                                                             │            │
│  │ Sales Invoice Updated:                                      │            │
│  │ ├─ custom_ebarimt_receipt_id: "ebarimt-ddtd"                │            │
│  │ └─ custom_ebarimt_lottery: "АА12345678"                     │            │
│  │                                                             │            │
│  │ eBarimt Receipt Log: (OPTIONAL - for audit trail only)      │            │
│  │ ├─ sales_invoice: "INV-2024-001"                            │            │
│  │ ├─ source: "QPay"  ← Indicates source                       │            │
│  │ └─ receipt_id: "ebarimt-ddtd"                               │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                             │
│  eBarimt App Hook (on Sales Invoice submit):                                │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ def on_submit_invoice(doc):                                 │            │
│  │     # Check if already has receipt (from ANY source)        │            │
│  │     if doc.custom_ebarimt_receipt_id:                       │            │
│  │         return  # SKIP - already done                       │            │
│  │                                                             │            │
│  │     # Check if QPay will handle it                          │            │
│  │     if settings.skip_if_qpay_ebarimt and has_qpay_invoice(doc): │        │
│  │         return  # SKIP - QPay will create eBarimt           │            │
│  │                                                             │            │
│  │     # Only create if no other source will                   │            │
│  │     submit_ebarimt_receipt(doc)                             │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 2: Cash Sale with eBarimt Only

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CASH SALE + eBARIMT FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step 1: POS Invoice Created & Submitted                                    │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ POS Invoice: POS-2024-001                                   │            │
│  │ ├─ customer: "Walk-in Customer"                             │            │
│  │ ├─ grand_total: 50,000                                      │            │
│  │ ├─ paid_amount: 50,000 (cash)                               │            │
│  │ └─ custom_ebarimt_receipt_id: (empty)                       │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                          │                                                  │
│                          ▼                                                  │
│  Step 2: eBarimt Hook Triggers (no QPay involved)                           │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ on_submit_pos_invoice(doc):                                 │            │
│  │ 1. No existing receipt → proceed                            │            │
│  │ 2. No QPay invoice → proceed                                │            │
│  │ 3. Submit to eBarimt POS API                                │            │
│  │ 4. Update POS Invoice with receipt_id, lottery              │            │
│  │ 5. Create eBarimt Receipt Log                               │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                          │                                                  │
│                          ▼                                                  │
│  Step 3: Records Created                                                    │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ POS Invoice Updated:                                        │            │
│  │ ├─ custom_ebarimt_receipt_id: "300123..."                   │            │
│  │ └─ custom_ebarimt_lottery: "ББ98765432"                     │            │
│  │                                                             │            │
│  │ eBarimt Receipt Log Created:                                │            │
│  │ ├─ pos_invoice: "POS-2024-001"                              │            │
│  │ ├─ source: "eBarimt"  ← Direct from eBarimt app             │            │
│  │ ├─ receipt_id: "300123..."                                  │            │
│  │ └─ lottery_number: "ББ98765432"                             │            │
│  │                                                             │            │
│  │ GL Entry (auto from POS Invoice):                           │            │
│  │ ├─ Dr: Cash 50,000                                          │            │
│  │ └─ Cr: Revenue 50,000                                       │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deduplication Rules

### Rule 1: eBarimt Receipt - Only ONE Source

```python
# Priority order for eBarimt creation:
EBARIMT_SOURCE_PRIORITY = [
    "QPay",      # 1st: If paid via QPay, QPay creates eBarimt
    "eBarimt",   # 2nd: If not QPay, eBarimt app creates directly
]

# In eBarimt Settings:
# ☑ Skip if QPay eBarimt exists (skip_if_qpay_ebarimt)

# Check before creating:
def should_create_ebarimt(doc):
    # Already has receipt from ANY source?
    if doc.get("custom_ebarimt_receipt_id"):
        return False
    
    # QPay will handle it?
    if has_pending_qpay_invoice(doc):
        return False
    
    return True
```

### Rule 2: Payment Entry - Only ONE per Payment

```python
# In QPay Settings:
# ☑ Auto Create Payment Entry (auto_create_payment_entry)

# Before creating Payment Entry:
def should_create_payment_entry(qpay_invoice):
    # Check if Payment Entry already exists for this invoice
    existing = frappe.db.exists("Payment Entry", {
        "custom_qpay_invoice": qpay_invoice.name
    })
    if existing:
        return False
    
    # Check if manual Payment Entry exists
    existing_manual = frappe.db.exists("Payment Entry", {
        "references": [["reference_name", "=", qpay_invoice.reference_name]]
    })
    if existing_manual:
        # Link existing to QPay instead of creating new
        link_payment_to_qpay(existing_manual, qpay_invoice)
        return False
    
    return True
```

### Rule 3: Reconciliation Check

```python
def reconcile_invoice(sales_invoice):
    """
    Ensure all related records are consistent.
    Call this before closing period or generating reports.
    """
    results = {
        "invoice": sales_invoice.name,
        "amount": sales_invoice.grand_total,
        "issues": []
    }
    
    # Check 1: Payment status
    outstanding = sales_invoice.outstanding_amount
    if outstanding > 0:
        results["issues"].append(f"Outstanding: {outstanding}")
    
    # Check 2: eBarimt receipt
    if not sales_invoice.custom_ebarimt_receipt_id:
        results["issues"].append("Missing eBarimt receipt")
    
    # Check 3: QPay vs eBarimt consistency
    qpay = get_qpay_invoice(sales_invoice.name)
    if qpay and qpay.ebarimt_created:
        if sales_invoice.custom_ebarimt_receipt_id != qpay.ebarimt_ddtd:
            results["issues"].append("eBarimt ID mismatch between QPay and Invoice")
    
    # Check 4: Payment Entry exists
    payments = get_payment_entries(sales_invoice.name)
    total_paid = sum(p.paid_amount for p in payments)
    if total_paid != sales_invoice.grand_total - outstanding:
        results["issues"].append(f"Payment mismatch: {total_paid} vs {sales_invoice.grand_total - outstanding}")
    
    return results
```

---

## Data Model Relationships

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSACTION DATA MODEL                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐         ┌─────────────────┐                            │
│  │    Company      │◄────────│  Sales Invoice  │                            │
│  │  (tax_id=PIN)   │         │                 │                            │
│  └────────┬────────┘         └────────┬────────┘                            │
│           │                           │                                     │
│           │                           │ 1:N                                 │
│           │                           ▼                                     │
│           │              ┌────────────────────────┐                         │
│           │              │                        │                         │
│           │         ┌────┴────┐             ┌────┴────┐                     │
│           │         ▼         ▼             ▼         ▼                     │
│           │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│           │   │  QPay    │ │ eBarimt  │ │ Payment  │ │ GL Entry │          │
│           │   │ Invoice  │ │ Receipt  │ │  Entry   │ │ (auto)   │          │
│           │   │          │ │   Log    │ │          │ │          │          │
│           │   └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────┘          │
│           │        │            │            │                              │
│           │        │ 1:1       │ 1:1        │ N:1                          │
│           │        │            │            │                              │
│           │        │            │            ▼                              │
│           │        │            │      ┌──────────┐                         │
│           │        │            │      │  Bank    │                         │
│           │        │            │      │ Account  │                         │
│           │        │            │      └──────────┘                         │
│           │        │            │                                           │
│           │        ▼            ▼                                           │
│           │   ┌─────────────────────┐                                       │
│           │   │     QPay API        │                                       │
│           │   │  (ebarimt_v3/...)   │                                       │
│           │   └─────────────────────┘                                       │
│           │              │                                                  │
│           │              ▼                                                  │
│           │   ┌─────────────────────┐                                       │
│           │   │    eBarimt API      │                                       │
│           │   │   (/rest/receipt)   │                                       │
│           │   └─────────────────────┘                                       │
│           │                                                                 │
│           │                                                                 │
│           │  REPORTING FLOW                                                 │
│           │  ═══════════════                                                │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────┐         ┌─────────────────┐                            │
│  │ eBalance Report │◄────────│  GL Entries     │                            │
│  │   (to MOF)      │         │ (aggregated)    │                            │
│  └─────────────────┘         └─────────────────┘                            │
│           │                                                                 │
│           │                                                                 │
│  ┌─────────────────┐         ┌─────────────────┐                            │
│  │  eTax Report    │◄────────│ eBarimt Receipts│                            │
│  │   (to MTA)      │         │  (VAT totals)   │                            │
│  └─────────────────┘         └─────────────────┘                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Relationships

| Parent Document | Child/Log Document | Relationship | Key Field |
|-----------------|-------------------|--------------|-----------|
| Sales Invoice | QPay Invoice | 1:1 or 0:1 | `reference_name` |
| Sales Invoice | eBarimt Receipt Log | 1:1 or 0:1 | `sales_invoice` |
| Sales Invoice | Payment Entry | 1:N | `references.reference_name` |
| QPay Invoice | Payment Entry | 1:1 | `custom_qpay_invoice` |
| POS Invoice | eBarimt Receipt Log | 1:1 | `pos_invoice` |
| Company | eBalance Report | 1:N | `company` |
| GL Entry | eBalance Report | N:1 | (aggregated) |

---

## Implementation: Duplicate Prevention

### 1. Add Source Tracking Field

```python
# Add to eBarimt Receipt Log
{
    "fieldname": "source",
    "fieldtype": "Select",
    "label": "Source",
    "options": "\neBarimt\nQPay",
    "description": "Which app created this receipt"
}

# Add to Payment Entry (custom field)
{
    "fieldname": "custom_payment_source",
    "fieldtype": "Select",
    "label": "Payment Source",
    "options": "\nManual\nQPay\nBank Import",
    "description": "How this payment was created"
}
```

### 2. Unique Constraints

```python
# In eBarimt Receipt Log
def validate(self):
    # Only one receipt per invoice
    if self.sales_invoice:
        existing = frappe.db.exists("eBarimt Receipt Log", {
            "sales_invoice": self.sales_invoice,
            "name": ["!=", self.name]
        })
        if existing:
            frappe.throw(f"Receipt already exists for {self.sales_invoice}: {existing}")
    
    if self.pos_invoice:
        existing = frappe.db.exists("eBarimt Receipt Log", {
            "pos_invoice": self.pos_invoice,
            "name": ["!=", self.name]
        })
        if existing:
            frappe.throw(f"Receipt already exists for {self.pos_invoice}: {existing}")
```

### 3. Cross-App Checks

```python
# ebarimt/integrations/sales_invoice.py

def on_submit_invoice(doc, method=None):
    """Check all sources before creating eBarimt"""
    
    # Check 1: Already has receipt ID on invoice
    if doc.get("custom_ebarimt_receipt_id"):
        return
    
    # Check 2: eBarimt Receipt Log exists
    if frappe.db.exists("eBarimt Receipt Log", {"sales_invoice": doc.name, "status": "Success"}):
        return
    
    # Check 3: QPay Invoice with eBarimt exists
    if frappe.db.exists("DocType", "QPay Invoice"):
        qpay = frappe.db.get_value("QPay Invoice", {
            "reference_doctype": "Sales Invoice",
            "reference_name": doc.name,
            "ebarimt_created": 1
        })
        if qpay:
            return
    
    # Check 4: Setting to skip
    settings = frappe.get_cached_doc("eBarimt Settings")
    if settings.skip_if_qpay_ebarimt:
        # Check if QPay invoice exists (will create eBarimt on payment)
        pending_qpay = frappe.db.exists("QPay Invoice", {
            "reference_doctype": "Sales Invoice",
            "reference_name": doc.name,
            "status": ["in", ["Draft", "Pending"]]
        })
        if pending_qpay:
            return
    
    # All checks passed - create eBarimt
    submit_ebarimt_receipt(doc)
```

### 4. Reconciliation Report

```python
# Create a reconciliation report

@frappe.whitelist()
def get_reconciliation_report(from_date, to_date, company=None):
    """
    Generate reconciliation report across all apps.
    Identifies:
    - Invoices without eBarimt
    - Duplicate eBarimt receipts
    - Payment mismatches
    - QPay vs eBarimt inconsistencies
    """
    
    filters = {
        "posting_date": ["between", [from_date, to_date]],
        "docstatus": 1
    }
    if company:
        filters["company"] = company
    
    invoices = frappe.get_all("Sales Invoice", filters=filters, fields=[
        "name", "grand_total", "outstanding_amount", 
        "custom_ebarimt_receipt_id", "custom_ebarimt_lottery"
    ])
    
    report = []
    
    for inv in invoices:
        row = {
            "invoice": inv.name,
            "amount": inv.grand_total,
            "outstanding": inv.outstanding_amount,
            "ebarimt_id": inv.custom_ebarimt_receipt_id,
            "issues": []
        }
        
        # Check eBarimt
        if not inv.custom_ebarimt_receipt_id:
            row["issues"].append("No eBarimt")
        
        # Check for duplicate eBarimt
        ebarimt_logs = frappe.get_all("eBarimt Receipt Log", 
            filters={"sales_invoice": inv.name},
            fields=["name", "receipt_id", "source"]
        )
        if len(ebarimt_logs) > 1:
            row["issues"].append(f"Duplicate eBarimt logs: {len(ebarimt_logs)}")
        
        # Check QPay
        if frappe.db.exists("DocType", "QPay Invoice"):
            qpay = frappe.db.get_value("QPay Invoice", {
                "reference_doctype": "Sales Invoice",
                "reference_name": inv.name
            }, ["name", "status", "ebarimt_created", "ebarimt_id"], as_dict=True)
            
            if qpay:
                row["qpay_invoice"] = qpay.name
                row["qpay_status"] = qpay.status
                
                # Check eBarimt consistency
                if qpay.ebarimt_created and qpay.ebarimt_id:
                    if inv.custom_ebarimt_receipt_id and inv.custom_ebarimt_receipt_id != qpay.ebarimt_id:
                        row["issues"].append("eBarimt ID mismatch")
        
        # Check payments
        payments = frappe.get_all("Payment Entry Reference",
            filters={"reference_doctype": "Sales Invoice", "reference_name": inv.name},
            fields=["parent", "allocated_amount"]
        )
        total_paid = sum(p.allocated_amount for p in payments)
        expected_paid = inv.grand_total - inv.outstanding_amount
        
        if abs(total_paid - expected_paid) > 0.01:
            row["issues"].append(f"Payment mismatch: {total_paid} vs {expected_paid}")
        
        if row["issues"]:
            report.append(row)
    
    return report
```

---

## Settings Configuration

### Recommended Settings for No Duplicates

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED SETTINGS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  QPay Settings:                                                             │
│  ├─ ☑ Enabled                                                               │
│  ├─ ☑ Auto Create Payment Entry                                             │
│  ├─ ☑ eBarimt Enabled (create via QPay API)                                 │
│  └─ ☑ Auto Create eBarimt on Payment                                        │
│                                                                             │
│  eBarimt Settings:                                                          │
│  ├─ ☑ Enabled                                                               │
│  ├─ ☑ Auto Submit on Invoice (for non-QPay invoices)                        │
│  ├─ ☑ Skip if QPay eBarimt exists ← KEY SETTING                             │
│  └─ ☑ Auto Void on Cancel                                                   │
│                                                                             │
│  Result:                                                                    │
│  ├─ QPay payments → eBarimt via QPay API                                    │
│  ├─ Cash/other payments → eBarimt via eBarimt app                           │
│  └─ No duplicates!                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary: Golden Rules

| Rule | Implementation |
|------|----------------|
| **One eBarimt per Invoice** | Check `custom_ebarimt_receipt_id` before creating |
| **One Payment Entry per Payment** | Check `custom_qpay_payment_id` before creating |
| **Source Tracking** | Add `source` field to track which app created record |
| **Cross-App Checks** | Check other apps' records before creating |
| **Master is ERPNext** | All app logs reference ERPNext documents |
| **Reconciliation** | Run reconciliation report before period close |

### Quick Checklist

Before going live:
- [ ] Enable `skip_if_qpay_ebarimt` in eBarimt Settings
- [ ] Configure QPay to create eBarimt automatically
- [ ] Add unique constraints to Receipt Log
- [ ] Test: QPay payment creates only ONE eBarimt
- [ ] Test: Cash sale creates only ONE eBarimt  
- [ ] Test: Cancellation voids eBarimt correctly
- [ ] Set up reconciliation report scheduled task
