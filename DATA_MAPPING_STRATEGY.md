# Data Mapping Strategy: Independent Apps ↔ ERPNext

## Principle
Each app works **independently** but can **read from** and **write to** ERPNext entities when needed.

---

## 1. ERPNext Entity Fields (Source of Truth)

### 1.1 Company (Self Organization)

| Field | Type | Description | Used By |
|-------|------|-------------|---------|
| `company_name` | Data | Legal name | All |
| `abbr` | Data | Abbreviation | All |
| `tax_id` | Data | **Registry Number (PIN)** - 7 digits | eTax, eBalance, eBarimt |
| `country` | Link | Country | All |
| `phone_no` | Data | Phone | All |
| `email` | Data | Email | All |
| `website` | Data | Website | All |
| `registration_details` | Code | Registration info JSON | All |

**Custom Fields (already exist):**
| Field | Type | Description | Used By |
|-------|------|-------------|---------|
| `custom_ebarimt_enabled` | Check | eBarimt enabled for company | eBarimt |
| `custom_operator_tin` | Data | Operator TIN (ЧЕ...) | eBarimt |
| `custom_pos_no` | Data | POS terminal number | eBarimt |
| `custom_merchant_tin` | Data | Merchant TIN | eBarimt |
| `ebalance_enabled` | Check | eBalance enabled | eBalance |
| `ebalance_org_id` | Data | eBalance org ID | eBalance |

---

### 1.2 Customer (Counterparty - B2B/B2C Sales)

| Field | Type | Description | Used By |
|-------|------|-------------|---------|
| `customer_name` | Data | Display name | All |
| `customer_type` | Select | Company/Individual | eBarimt |
| `tax_id` | Data | **TIN or Registry** (general) | All |

**Custom Fields (already exist):**
| Field | Type | Description | Used By |
|-------|------|-------------|---------|
| `ebarimt_type` | Select | CITIZEN/COMPANY | eBarimt, QPay |
| `ebarimt_register` | Data | eBarimt register ID | eBarimt |
| `custom_tin` | Data | **TIN** (Taxpayer ID) | eBarimt, eTax |
| `custom_regno` | Data | **Registry Number** (PIN) | All |
| `custom_vat_payer` | Check | Is VAT payer | eBarimt |
| `custom_city_payer` | Check | Pays city tax | eBarimt |
| `custom_taxpayer_name` | Data | Official name from tax authority | eBarimt |
| `custom_taxpayer_synced` | Check | Data synced from API | eBarimt |
| `custom_is_foreigner` | Check | Foreign customer | eBarimt |
| `custom_ebarimt_customer_no` | Data | eBarimt customer number | eBarimt |

---

### 1.3 Supplier (Counterparty - Purchases)

| Field | Type | Description | Used By |
|-------|------|-------------|---------|
| `supplier_name` | Data | Display name | All |
| `supplier_type` | Select | Company/Individual | - |
| `tax_id` | Data | **TIN or Registry** | eBalance, eBarimt |

**Custom Fields Needed:**
| Field | Type | Description | Used By |
|-------|------|-------------|---------|
| `custom_tin` | Data | TIN | eBarimt (purchase receipts) |
| `custom_regno` | Data | Registry Number | eBalance |

---

## 2. Mapping from Apps to ERPNext

### 2.1 eTax → ERPNext

**eTax getUserOrgs API returns:**
```json
{
  "id": 10741903,           // ent_id
  "tin": "15200005097",     // TIN
  "pin": "6709389",         // Registry Number
  "entityName": "Дижитал консалтинг сервис",
  "entType": 2              // 1=Individual, 2=Legal Entity
}
```

**Mapping to Company:**
| eTax Field | ERPNext Company Field |
|------------|----------------------|
| `pin` | `tax_id` |
| `tin` | Store in Settings only (not on Company) |
| `entityName` | Verify matches `company_name` |
| `id` | Store in `eTax Settings.ent_id` |

**Read from ERPNext:**
```python
# eTax Settings should read org_regno from Company
company = frappe.defaults.get_defaults().company
if company:
    org_regno = frappe.db.get_value("Company", company, "tax_id")
```

---

### 2.2 eBalance → ERPNext

**eBalance API uses:**
- `orgRegNo` - Organization registry number
- `userRegNo` - User personal registry number

**Mapping to Company:**
| eBalance Field | ERPNext Company Field |
|----------------|----------------------|
| `orgRegNo` | `tax_id` |
| Company link | `eBalance Settings.company` |

**Read from ERPNext:**
```python
# eBalance should link to Company and read tax_id
company_name = self.settings.company
if company_name:
    org_regno = frappe.db.get_value("Company", company_name, "tax_id")
```

---

### 2.3 eBarimt → ERPNext

**eBarimt uses:**
- `merchant_tin` - Company TIN
- `pos_no` - POS terminal
- `customer_tin` - Customer TIN for B2B receipts

**Mapping to Company (self):**
| eBarimt Field | ERPNext Company Field |
|---------------|----------------------|
| `merchant_tin` | `custom_merchant_tin` |
| `operator_tin` | `custom_operator_tin` |
| `pos_no` | `custom_pos_no` |

**Mapping to Customer (counterparty):**
| eBarimt Field | ERPNext Customer Field |
|---------------|----------------------|
| `customer_tin` | `custom_tin` |
| Receiver type | `ebarimt_type` (CITIZEN/COMPANY) |
| VAT payer status | `custom_vat_payer` |
| Official name | `custom_taxpayer_name` |

**Write to ERPNext (after TIN lookup):**
```python
# After eBarimt checkTin API call
def update_customer_from_tin(customer_name, tin_data):
    customer = frappe.get_doc("Customer", customer_name)
    customer.custom_tin = tin_data.get("tin")
    customer.custom_taxpayer_name = tin_data.get("name")
    customer.custom_vat_payer = tin_data.get("found", False)
    customer.custom_taxpayer_synced = True
    customer.save()
```

---

### 2.4 QPay → ERPNext

**QPay Invoice uses:**
- `receiver_register` - Customer registry
- `receiver_name` - Customer name

**Mapping to Customer:**
| QPay Field | ERPNext Customer Field |
|------------|----------------------|
| `receiver_register` | `custom_regno` or `custom_tin` |
| `receiver_name` | `customer_name` |
| `ebarimt_receiver_type` | `ebarimt_type` |

**Link to Sales Invoice:**
| QPay Field | ERPNext Field |
|------------|---------------|
| `reference_doctype` | "Sales Invoice" |
| `reference_name` | Sales Invoice name |

---

## 3. Strategy: Read First, Store Locally

### Pattern for Each App:

```python
class AppSettings:
    def get_org_regno(self):
        """Get organization registry number"""
        # 1. Check if set in app settings
        if self.org_regno:
            return self.org_regno
        
        # 2. Read from linked ERPNext Company
        company = self.company or frappe.defaults.get_defaults().company
        if company:
            regno = frappe.db.get_value("Company", company, "tax_id")
            if regno:
                return regno
        
        # 3. Return None - requires manual entry
        return None
```

### Customer TIN Pattern:

```python
def get_customer_tin(customer_name):
    """Get customer TIN for eBarimt/QPay"""
    customer = frappe.get_doc("Customer", customer_name)
    
    # Priority: custom_tin > tax_id > ebarimt_register
    return customer.custom_tin or customer.tax_id or customer.ebarimt_register
```

---

## 4. Field Usage Matrix

### Company Fields by App:

| ERPNext Field | QPay | eBarimt | eBalance | eTax |
|---------------|------|---------|----------|------|
| `company_name` | - | - | ✓ | ✓ |
| `tax_id` (Registry) | - | - | ✓ Read | ✓ Read |
| `custom_merchant_tin` | - | ✓ R/W | - | - |
| `custom_operator_tin` | - | ✓ R/W | - | - |
| `custom_pos_no` | - | ✓ R/W | - | - |
| `ebalance_enabled` | - | - | ✓ R/W | - |
| `ebalance_org_id` | - | - | ✓ R/W | - |

### Customer Fields by App:

| ERPNext Field | QPay | eBarimt | eBalance | eTax |
|---------------|------|---------|----------|------|
| `customer_name` | ✓ Read | ✓ Read | - | - |
| `tax_id` | ✓ Read | ✓ Read | - | - |
| `custom_tin` | ✓ Read | ✓ R/W | - | - |
| `custom_regno` | ✓ Read | ✓ R/W | - | - |
| `custom_vat_payer` | - | ✓ R/W | - | - |
| `ebarimt_type` | ✓ Read | ✓ R/W | - | - |
| `ebarimt_register` | ✓ Read | ✓ R/W | - | - |
| `custom_taxpayer_name` | - | ✓ Write | - | - |
| `custom_taxpayer_synced` | - | ✓ Write | - | - |

---

## 5. Data Flow Diagrams

### 5.1 eTax - Read Company for org_regno
```
eTax Settings                     ERPNext
┌─────────────┐                 ┌─────────────┐
│ org_regno ←─────── READ ──────│ Company     │
│             │                 │ .tax_id     │
│ ent_id      │                 └─────────────┘
│ (from API)  │
└─────────────┘
```

### 5.2 eBarimt - Read Customer, Write after TIN lookup
```
Sales Invoice      eBarimt                Customer
┌───────────┐    ┌──────────────┐      ┌─────────────┐
│ customer ─────→│ checkTin API │      │             │
│           │    │              │      │ custom_tin  │
└───────────┘    │   Result ────────→  │ custom_vat  │
                 │              │      │ taxpayer_nm │
                 └──────────────┘      └─────────────┘
```

### 5.3 QPay - Read Customer for receiver data
```
QPay Invoice                        Customer
┌────────────────┐                ┌─────────────┐
│ receiver_reg ←────── READ ──────│ custom_tin  │
│ receiver_name←────── READ ──────│ customer_nm │
│ ebarimt_type ←────── READ ──────│ ebarimt_type│
└────────────────┘                └─────────────┘
```

### 5.4 eBalance - Read Company for org_regno
```
eBalance Settings                  ERPNext
┌─────────────┐                 ┌─────────────┐
│ company ────────── LINK ──────│ Company     │
│ org_regno ←──────  READ ──────│ .tax_id     │
└─────────────┘                 └─────────────┘
```

---

## 6. Implementation Guidelines

### 6.1 Each App Should:

1. **Have its own Settings DocType** - Store app-specific config
2. **Link to Company** - Reference ERPNext Company (optional)
3. **Read ERPNext fields** - When available, don't duplicate entry
4. **Store API responses locally** - Keep app-specific data in app DocTypes
5. **Write back to ERPNext** - When enriching Customer/Supplier data

### 6.2 Each App Should NOT:

1. ❌ Require other MN apps to be installed
2. ❌ Modify other app's DocTypes
3. ❌ Store duplicate master data (Districts, Tax Codes) if already in another app
4. ❌ Require ERPNext fields to be filled - allow manual entry in Settings

### 6.3 Optional ERPNext Integration:

Each app should have a flag like:
```python
# In Settings
enable_erpnext_integration = Check  # Default: False

# In code
if self.settings.enable_erpnext_integration:
    # Read from ERPNext
    regno = frappe.db.get_value("Company", company, "tax_id")
else:
    # Use value from app Settings
    regno = self.settings.org_regno
```

---

## 7. Summary Table

| Data | Stored In | QPay | eBarimt | eBalance | eTax |
|------|-----------|------|---------|----------|------|
| Self Registry (PIN) | `Company.tax_id` | - | - | Read | Read |
| Self TIN | App Settings | - | Write | - | Store |
| Self ent_id | App Settings | - | - | - | Store |
| POS No | `Company.custom_pos_no` | - | R/W | - | - |
| Merchant TIN | `Company.custom_merchant_tin` | - | R/W | - | - |
| Customer TIN | `Customer.custom_tin` | Read | R/W | - | - |
| Customer VAT | `Customer.custom_vat_payer` | - | R/W | - | - |
| Customer Type | `Customer.ebarimt_type` | Read | R/W | - | - |

---

## 8. Conclusion

**Apps remain independent:**
- Each app has its own Settings, DocTypes, and logic
- No cross-app dependencies
- Works without ERPNext (manual entry in Settings)

**ERPNext integration is optional:**
- When linked to Company, read registry number from `tax_id`
- When processing Customers, read/write tax fields
- Enriches ERPNext data without requiring it
