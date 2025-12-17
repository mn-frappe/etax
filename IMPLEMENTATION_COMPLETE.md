# Multi-Company Entity Architecture - Implementation Complete

## Summary

Implemented ERPNext Company as the central entity for all 4 MN apps (eTax, eBarimt, eBalance, QPay) with **multi-company support**.

## Key Concept: Document-Driven Entity Resolution

All ERPNext documents (Sales Invoice, Purchase Invoice, etc.) have a `company` field. The MN apps now read entity configuration from the **document's company**, not from global settings.

```
┌────────────────────────────────────────────────────────────────┐
│                    Sales Invoice                                │
│                    company: "ABC LLC"                           │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│              get_entity_for_doc(sales_invoice)                  │
│              Returns MNEntity for "ABC LLC"                     │
└────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
         eTax            eBarimt             QPay
    (same entity)    (same entity)     (same entity)
```

## Usage

### From Any MN App

```python
from etax.mn_entity import get_entity_for_doc, get_entity_for_company

# From a document (PREFERRED - ensures all apps use same entity)
doc = frappe.get_doc("Sales Invoice", "SINV-00001")
entity = get_entity_for_doc(doc)

# Access entity properties
org_regno = entity.org_regno      # PIN / Registry Number
tin = entity.tin                  # TIN (11 digits)
merchant_tin = entity.merchant_tin
operator_tin = entity.operator_tin
pos_no = entity.pos_no
district_code = entity.district_code
ebarimt_enabled = entity.ebarimt_enabled

# Validate required fields
entity.validate()                  # For eTax (requires org_regno)
entity.validate(require_ebarimt=True)  # For eBarimt (requires merchant_tin, pos_no)
```

### From JavaScript

```javascript
frappe.call({
    method: 'etax.mn_entity.get_entity_info',
    args: {
        doctype: 'Sales Invoice',
        docname: 'SINV-00001'
    },
    callback: function(r) {
        console.log(r.message.merchant_tin);
    }
});
```

## Company Custom Fields

### On Company DocType
| Field | Type | Label | Purpose |
|-------|------|-------|---------|
| `tax_id` | Data | Tax ID | PIN / Registry Number (built-in) |
| `custom_tin` | Data | TIN (ТИН) | 11-digit Taxpayer ID from MTA |
| `custom_ent_id` | Data | MTA Entity ID | Entity ID (auto-filled) |
| `custom_merchant_tin` | Data | Merchant TIN | eBarimt Merchant TIN (ТТДД) |
| `custom_operator_tin` | Data | Operator TIN | eBarimt Operator TIN |
| `custom_pos_no` | Data | POS No | eBarimt POS Number |
| `custom_district_code` | Link | Default District | Default district for receipts |
| `custom_ebarimt_enabled` | Check | Enable eBarimt | Is eBarimt enabled for company |

## Multi-Company Configuration

### Step 1: Configure Each Company
```
Company: "ABC LLC"
├── Tax ID: "6709389" (PIN)
├── TIN (ТИН): "15200005097"
├── Merchant TIN: "15200005097"
├── Operator TIN: "15200005097"
├── POS No: "10003470"
├── Default District: "Khan-Uul (23)"
└── Enable eBarimt: ✅

Company: "XYZ LLC"
├── Tax ID: "1234567" (PIN)
├── TIN (ТИН): "98765432101"
├── Merchant TIN: "98765432101"
...
```

### Step 2: Settings (Global Defaults)
Settings DocTypes now have `company` field for fallback:
- eTax Settings → Company (default for standalone use)
- eBarimt Settings → Company (default for standalone use)
- QPay Settings → Company (default for standalone use)

**Important**: When processing a document, the app uses the **document's company**, not the settings company.

### Step 3: Enable Duplicate Prevention

**eBarimt Settings:**
| Setting | Value | Why |
|---------|-------|-----|
| Skip if QPay eBarimt | ✅ | Prevents duplicate receipts |
| Auto Void on Cancel | ✅ | Auto-voids if doc cancelled |

**QPay Settings:**
| Setting | Value | Why |
|---------|-------|-----|
| eBarimt Enabled | ✅ | QPay sends to eBarimt |
| Auto Create Payment Entry | ✅ | Auto-create ERPNext Payment |

## Deduplication Logic

```
Sales Invoice submitted
    │
    ▼
QPay enabled? ────Yes───► Create QPay Invoice
    │                         │
    No                        ▼
    │                    QPay eBarimt enabled?
    ▼                         │
eBarimt ◄──────No────────────┘
enabled?                      │
    │                        Yes
    │                         │
   Yes                        ▼
    │                    QPay sends eBarimt
    ▼
skip_if_qpay_ebarimt? ───Yes──► Skip (already sent by QPay)
    │
    No
    │
    ▼
Send eBarimt from eBarimt app
```

## Verification Commands

```bash
# Test multi-company entity resolution
bench --site YOUR_SITE execute "
from etax.mn_entity import get_entity_for_company
entity = get_entity_for_company('Your Company Name')
print(entity.to_dict())
"

# Test from document
bench --site YOUR_SITE execute "
import frappe
from etax.mn_entity import get_entity_for_doc
doc = frappe.get_doc('Sales Invoice', 'SINV-00001')
entity = get_entity_for_doc(doc)
print(f'Document company: {doc.company}')
print(f'Entity: {entity.to_dict()}')
"
```

## What's NOT Changed

- Apps remain independent (can work without Company link)
- Single-company setups work exactly as before
- Legacy functions still work (with deprecation warnings)

## Module Structure

```
etax/
├── mn_entity.py          # MAIN: Multi-company entity resolver
├── utils/
│   └── company.py        # Legacy wrapper (imports from mn_entity)

ebarimt/
├── mn_entity.py → symlink to etax/mn_entity.py
├── utils/
│   └── company.py        # Legacy wrapper

qpay/
├── mn_entity.py → symlink to etax/mn_entity.py
└── company.py            # Legacy wrapper
```

## Next Steps

1. Configure each Company with tax fields
2. Enable `skip_if_qpay_ebarimt` in eBarimt Settings (already enabled)
3. Test by creating Sales Invoice for each company
