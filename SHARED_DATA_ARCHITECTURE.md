# Shared Data Architecture Analysis

## Overview

This document analyzes data collected by 4 Mongolian government integration apps and proposes a unified architecture to prevent data duplication while maintaining app independence.

---

## 1. Data Collection by Each App

### 1.1 QPay (Payment Gateway)
**Source:** QPay Bank API  
**Primary Purpose:** Payment processing

| Data Type | Storage | Source API |
|-----------|---------|------------|
| Invoices | `QPay Invoice` | createInvoice, getPayment |
| Payments | `QPay Payment` | callback, getPayment |
| Banks | `QPay Bank` | Static/Config |
| Districts | `QPay District` | Static/Config |
| Product Codes (GS1) | `QPay Product Code` | eBarimt sync |
| eBarimt data (optional) | Fields in QPay Invoice | Via eBarimt app |

**Key Organization Data:**
- `receiver_register` - Customer/Company registry number
- `receiver_name` - Name
- eBarimt fields: `ebarimt_receiver_type`, `ebarimt_receiver`, `ebarimt_ddtd`

---

### 1.2 eBarimt (Tax Receipts)
**Source:** eBarimt POS API, Public API, ITC Service  
**Primary Purpose:** Tax receipt generation & reporting

| Data Type | Storage | Source API |
|-----------|---------|------------|
| Receipts | `eBarimt Receipt Log` | put (POS API) |
| Tax Codes | `eBarimt Tax Code` | getInformation |
| Product Codes (GS1) | `eBarimt Product Code` | getInformation |
| Districts | `eBarimt District` | Static/Config |
| Payment Types | `eBarimt Payment Type` | Static |
| OAT Products | `eBarimt OAT Product Type` | OAT API |

**Key Organization Data (from Settings):**
- `merchant_tin` - Company TIN (Taxpayer ID)
- `operator_tin` - Operator TIN
- `pos_no` - POS terminal number
- `district_code` - Business location

**Customer TIN Lookup:**
- API: `checkTin` - Verifies customer TIN and returns name
- Stores: `customer_tin` in receipt, links to ERPNext Customer `tax_id`

---

### 1.3 eBalance (MOF Financial Reporting)
**Source:** MOF eBalance Inspector Service  
**Primary Purpose:** Financial statement submission

| Data Type | Storage | Source API |
|-----------|---------|------------|
| Report Periods | `eBalance Report Period` | getWritingConfigs |
| Report Requests | `eBalance Report Request` | getReportUserOrgHdrList |
| Account Mappings | `MOF Account Mapping` | getReportPackageMap |
| Submission Logs | `eBalance Submission Log` | sendReportData |

**Key Organization Data (from Settings):**
- `org_regno` - Company registry number (7 digits)
- `user_regno` - User's personal registry (2 letters + 8 digits)
- `company` - Link to ERPNext Company

**Organization Data from API:**
```json
{
  "regNum": "6709389",
  "legalName": "Дижитал консалтинг сервис",
  "reportOrgStatusCode": "CONFIRMED"
}
```

---

### 1.4 eTax (MTA Tax Returns)
**Source:** MTA eTax API  
**Primary Purpose:** Tax return filing

| Data Type | Storage | Source API |
|-----------|---------|------------|
| Organizations | `eTax Taxpayer` | getUserOrgs |
| Tax Reports | `eTax Report` | getList, getHistory |
| Report Forms | `eTax Report Form` | getFormList, getFormDetail |
| Sheet Forms | `eTax Sheet Form` | getSheetList |
| Submissions | `eTax Submission Log` | submit |

**Key Organization Data (from getUserOrgs API):**
```json
{
  "id": 10741903,           // ent_id - used for API calls
  "tin": "15200005097",     // Taxpayer Identification Number
  "pin": "6709389",         // Registry Number
  "entityName": "Дижитал консалтинг сервис",
  "entType": 2,             // 1=Individual, 2=Legal Entity
  "taxpayerBranchView": {
    "branchCode": "24",
    "branchName": "Баянзүрх",
    "subBranchCode": "2425",
    "subBranchName": "25-р хороо"
  }
}
```

---

## 2. Data Overlap Analysis

### 2.1 Organization/Entity Data (CRITICAL OVERLAP)

| Field | QPay | eBarimt | eBalance | eTax | ERPNext |
|-------|------|---------|----------|------|---------|
| Registry No (PIN) | `receiver_register` | - | `org_regno` | `pin` | `Company.tax_id` |
| TIN | - | `merchant_tin` | - | `tin` | `custom_merchant_tin` |
| Entity Name | `receiver_name` | - | From API | `entityName` | `Company.company_name` |
| Entity Type | - | - | - | `entType` | - |
| Branch Code | - | `district_code` | - | `branchCode` | - |

**Problem:** Same organization data stored in 4+ places with different field names.

---

### 2.2 Customer/Counterparty Data

| Field | QPay | eBarimt | ERPNext |
|-------|------|---------|---------|
| Customer Registry | `receiver_register` | `customer_tin` | `custom_regno` |
| Customer TIN | - | `customer_tin` | `custom_tin`, `tax_id` |
| Customer Name | `receiver_name` | From checkTin API | `customer_name` |
| Is VAT Payer | - | From checkTin API | `custom_vat_payer` |

**Problem:** Customer TIN verification happens separately in each app.

---

### 2.3 Product Classification (GS1/UNSPSC)

| Field | QPay | eBarimt |
|-------|------|---------|
| Code | `product_code` | `classification_code` |
| Segment | `segment_code` | `segment_code` |
| Family | `family_code` | `family_code` |
| Class | `class_code` | `class_code` |
| Brick | `brick_code` | `brick_code` |
| VAT Type | `vat_type` | `vat_type` |

**Problem:** Duplicate DocTypes for same GS1 classification data.

---

### 2.4 Geographic Districts

| Field | QPay District | eBarimt District |
|-------|---------------|------------------|
| Code | `district_code` | `code` |
| Name | `sub_branch_name` | `name_mn` |
| Parent | `branch_code/name` | `aimag` |

**Problem:** Same district data with different structures.

---

## 3. ERPNext Integration Points

### 3.1 Current Custom Fields on ERPNext DocTypes

**Company:**
- `custom_operator_tin` - eBarimt operator TIN
- `custom_merchant_tin` - eBarimt merchant TIN

**Customer:**
- `custom_tin` - Taxpayer ID
- `custom_regno` - Registry number
- `custom_vat_payer` - VAT payer status
- `custom_taxpayer_name` - Official name from tax authority
- `custom_taxpayer_synced` - Sync status flag
- `ebarimt_register` - eBarimt-specific register

**Sales Invoice / POS Invoice:**
- Links to `eBarimt Receipt Log`
- Links to `QPay Invoice`

---

## 4. Proposed Shared Data Architecture

### 4.1 Core Shared DocTypes (New App: `mn_core` or use existing)

#### Option A: Create new shared app `mn_core`

```
mn_core/
├── mn_core/
│   └── doctype/
│       ├── mn_organization/        # Unified taxpayer/organization
│       ├── mn_district/            # Unified districts
│       ├── mn_product_code/        # Unified GS1 codes
│       └── mn_tax_code/            # Unified tax codes
```

#### Option B: Extend ERPNext Company/Customer with Custom Fields

Use ERPNext's `Company` and `Customer` as the single source of truth:

**Company (Self Organization):**
```
tax_id          → Registry Number (PIN) - EXISTING
custom_tin      → Taxpayer ID (TIN)
custom_ent_id   → eTax Entity ID
custom_pos_no   → eBarimt POS Number
custom_branch_code → Tax office branch
```

**Customer (Counterparty):**
```
custom_regno    → Registry Number - EXISTING
custom_tin      → TIN - EXISTING
custom_vat_payer → VAT status - EXISTING
```

---

### 4.2 Recommended Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ERPNext Core                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │   Company    │    │   Customer   │    │  Item (with GS1)    │   │
│  │  (Self Org)  │    │ (Counterpty) │    │                      │   │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘   │
│         │                   │                       │               │
└─────────┼───────────────────┼───────────────────────┼───────────────┘
          │                   │                       │
          ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Shared Data Layer                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │ MN District  │    │ MN Tax Code  │    │   MN Product Code    │   │
│  │   (shared)   │    │   (shared)   │    │      (GS1)           │   │
│  └──────────────┘    └──────────────┘    └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │                   │                       │
    ┌─────┴─────┬─────────────┼─────────────┬────────┴────┐
    │           │             │             │             │
    ▼           ▼             ▼             ▼             ▼
┌───────┐ ┌─────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ QPay  │ │eBarimt  │ │ eBalance  │ │   eTax    │ │  Future   │
│       │ │         │ │           │ │           │ │   Apps    │
└───────┘ └─────────┘ └───────────┘ └───────────┘ └───────────┘
```

---

### 4.3 Settings Consolidation

Instead of 4 separate settings with duplicate credentials:

**Current (Problematic):**
- QPay Settings: username, password, environment
- eBarimt Settings: username, password, environment, merchant_tin, district
- eBalance Settings: username, password, org_regno, user_regno
- eTax Settings: username, password, org_regno, ne_key

**Proposed (Shared MN Settings or Extend Company):**

```python
# On Company DocType - Custom Fields:
{
    # Organization Identity
    "mn_registry_no": "6709389",        # PIN - Registry Number
    "mn_tin": "15200005097",            # TIN - Taxpayer ID
    "mn_ent_id": 10741903,              # eTax entity ID
    
    # Tax Office Location
    "mn_branch_code": "24",
    "mn_branch_name": "Баянзүрх",
    "mn_sub_branch_code": "2425",
    
    # eBarimt POS
    "mn_pos_no": "10012345",
    "mn_operator_tin": "ЧЕ79123134",
    
    # ITC Account (shared across eTax, eBalance, eBarimt public API)
    "mn_itc_username": "ЧЕ79123134",
    # Password stored via get_password()
}
```

---

## 5. Data Sharing Strategy

### 5.1 Read from ERPNext Core First

Each app should check ERPNext core data before storing duplicates:

```python
# Example: eTax getting organization info
def get_organization_info(self):
    # First check if Company has the data
    company = frappe.get_doc("Company", frappe.defaults.get_defaults().company)
    
    if company.tax_id and company.custom_tin:
        return {
            "pin": company.tax_id,
            "tin": company.custom_tin,
            "name": company.company_name,
            "ent_id": company.custom_ent_id
        }
    
    # Fetch from API and update Company
    org_data = self.api.get_user_orgs()
    company.custom_tin = org_data.get("tin")
    company.custom_ent_id = org_data.get("id")
    company.save()
    
    return org_data
```

### 5.2 Customer TIN Lookup - Shared Service

Create a shared utility that all apps use:

```python
# mn_utils/taxpayer.py (or in frappe app)
def lookup_taxpayer(tin_or_regno):
    """
    Unified taxpayer lookup used by all apps.
    Updates ERPNext Customer with verified data.
    
    Sources (in order):
    1. ERPNext Customer (cached)
    2. eBarimt checkTin API
    3. eTax getUserOrgs (for self)
    """
    # Check cache first
    customer = frappe.db.get_value("Customer", 
        {"custom_tin": tin_or_regno}, 
        ["name", "customer_name", "custom_vat_payer"], 
        as_dict=True
    )
    
    if customer and customer.custom_taxpayer_synced:
        return customer
    
    # Call eBarimt API
    from ebarimt.api.client import EBarimtClient
    result = EBarimtClient().check_tin(tin_or_regno)
    
    if result:
        # Update or create Customer
        update_customer_from_tin_lookup(tin_or_regno, result)
    
    return result
```

### 5.3 Product Code - Single Source

Keep `eBarimt Product Code` as the master (it has more fields), deprecate `QPay Product Code`:

```python
# QPay can link to eBarimt Product Code
class QPay Invoice Item:
    product_code = Link("eBarimt Product Code")  # Instead of separate DocType
```

### 5.4 District - Single Source

Keep `eBarimt District` as master (has English names), add fields QPay needs:

```python
# Add to eBarimt District:
branch_code = Data()      # For QPay/eTax compatibility
sub_branch_code = Data()
```

---

## 6. Implementation Priority

### Phase 1: Non-Breaking (Immediate)
1. Add utility functions for shared lookups
2. Add Company custom fields for MN-specific data
3. Ensure apps READ from Company first

### Phase 2: Consolidation (Next Release)
1. Migrate QPay Product Code → eBarimt Product Code
2. Migrate QPay District → eBarimt District
3. Update all apps to use shared references

### Phase 3: Full Integration (Future)
1. Create `MN Settings` DocType consolidating all credentials
2. Single ITC auth handler shared by all apps
3. Unified token storage/refresh

---

## 7. Current Custom Fields Audit

### On Company (already exist):
- `custom_operator_tin` ✓
- `custom_merchant_tin` ✓

### On Customer (already exist):
- `custom_tin` ✓
- `custom_regno` ✓
- `custom_vat_payer` ✓
- `custom_taxpayer_name` ✓
- `custom_taxpayer_synced` ✓

### Needed on Company:
- `custom_ent_id` - eTax entity ID
- `custom_ne_key` - eTax NE-KEY (password field)
- `custom_pos_no` - eBarimt POS number
- `custom_branch_code` - Tax office
- `custom_itc_username` - Shared ITC username

---

## 8. Summary Table

| Data Type | Current Owner | Recommended Owner | Other Apps Use |
|-----------|--------------|-------------------|----------------|
| Self Organization | Each Settings | ERPNext Company | Link/Read |
| Customer TIN | eBarimt, QPay | ERPNext Customer | Shared lookup |
| Product Codes (GS1) | eBarimt, QPay | eBarimt Product Code | Link |
| Districts | eBarimt, QPay | eBarimt District | Link |
| Tax Codes | eBarimt | eBarimt Tax Code | Link |
| ITC Auth Token | Each Settings | Company or Shared | Shared service |

---

## 9. Next Steps

1. **Review this document** with team
2. **Decide on approach** (Option A vs B)
3. **Create shared utility module** for taxpayer lookup
4. **Add missing custom fields** to Company
5. **Update apps** to read from ERPNext first
6. **Deprecate duplicate DocTypes** gradually
