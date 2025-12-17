# Entity Consolidation Strategy

## The Problem

We have **5 different places** storing what is essentially the **same legal entity**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE SAME COMPANY (e.g., "Дижитал консалтинг сервис")     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ERPNext Company          eTax Settings         eBarimt Settings            │
│  ├─ tax_id: (empty)       ├─ org_regno: 6709389 ├─ merchant_tin: 37900...   │
│  ├─ company_name          ├─ org_name           ├─ operator_tin: 23354...   │
│  └─ (no TIN field)        ├─ taxpayer_tin       └─ pos_no: 10011702         │
│                           └─ ent_id: 10741903                               │
│                                                                             │
│  eBalance Settings        QPay Settings                                     │
│  ├─ org_regno: 6709389    ├─ username                                       │
│  ├─ company: Wind Power   ├─ invoice_code                                   │
│  └─ user_regno            └─ (no org fields)                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Issues:

1. **Data Duplication** - Same org_regno stored in eTax, eBalance, potentially others
2. **Data Inconsistency** - Different company names, missing TINs
3. **No Single Source of Truth** - Each app maintains its own copy
4. **ERPNext Company is incomplete** - Missing TIN, custom fields not populated

---

## Understanding the Entities

### Legal Entity Identifiers in Mongolia

| Identifier | Name | Format | Issuing Authority | Purpose |
|------------|------|--------|-------------------|---------|
| **PIN** | Registration Number (РД) | 7 digits | State Registration | Company registry |
| **TIN** | Taxpayer ID (ТИН) | 11 digits | Tax Authority (MTA) | Tax identification |
| **Merchant TIN** | Merchant Tax ID | 11 digits | eBarimt | VAT receipt merchant |
| **Operator TIN** | Operator Tax ID | 11 digits | eBarimt | POS operator |
| **POS No** | POS Terminal Number | 8 digits | eBarimt | Receipt terminal |

### Key Insight: PIN ↔ TIN Relationship

```
Company Registry (PIN: 6709389)
    ↓
    ↓  MTA registers for taxes
    ↓
Tax Authority assigns TIN (TIN: 15200005097)
    ↓
    ↓  Company registers for eBarimt
    ↓
eBarimt assigns Merchant TIN, Operator TIN, POS No
```

**The PIN (Registry Number) is the PRIMARY KEY that links everything.**

---

## Proposed Architecture

### Principle: ERPNext Company as the Central Entity

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ERPNext Company (Single Source of Truth)            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Core Fields:                       MN Tax Custom Fields:                   │
│  ├─ name: "Wind Power LLC"          ├─ tax_id: "6709389" (PIN)              │
│  ├─ company_name                    ├─ custom_tin: "15200005097" (TIN)      │
│  └─ abbr                            ├─ custom_merchant_tin                  │
│                                     ├─ custom_operator_tin                  │
│                                     ├─ custom_pos_no                        │
│                                     ├─ custom_district_code                 │
│                                     └─ custom_ent_id (MTA entity ID)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
                ▼                     ▼                     ▼
┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────────┐
│    eTax Settings      │ │  eBarimt Settings │ │   eBalance Settings   │
├───────────────────────┤ ├───────────────────┤ ├───────────────────────┤
│ company: Link ────────┼─┼───────────────────┼─┤ company: Link ────────│
│                       │ │ company: Link ────│ │                       │
│ # Reads from Company: │ │                   │ │ # Reads from Company: │
│ # - org_regno (PIN)   │ │ # Reads from Co.: │ │ # - org_regno (PIN)   │
│ # - taxpayer_tin      │ │ # - merchant_tin  │ │                       │
│ # - ent_id            │ │ # - operator_tin  │ │ # Own fields:         │
│                       │ │ # - pos_no        │ │ # - user_regno        │
│ # Own fields:         │ │ # - district_code │ │ # - per_map_role_id   │
│ # - username          │ │                   │ │                       │
│ # - password          │ │ # Own fields:     │ │ # API credentials:    │
│ # - ne_key            │ │ # - username      │ │ # - username          │
│ # - API credentials   │ │ # - password      │ │ # - password          │
│                       │ │ # - API settings  │ │                       │
└───────────────────────┘ └───────────────────┘ └───────────────────────┘
                │                     │                     │
                ▼                     ▼                     ▼
         MTA API (eTax)      eBarimt API (POS)     MOF API (eBalance)
```

---

## Implementation Strategy

### Phase 1: Add Company Link to Each App Settings

Each app settings should have an **optional** Company link:

```python
# In each app's Settings DocType
{
    "fieldname": "company",
    "fieldtype": "Link",
    "options": "Company",
    "label": "Company",
    "description": "Link to ERPNext Company. If set, reads org info from Company."
}
```

### Phase 2: Add Custom Fields to Company

```python
# Company custom fields for MN integrations
COMPANY_CUSTOM_FIELDS = {
    "Company": [
        # Tax Authority (MTA) fields
        {
            "fieldname": "mn_tax_section",
            "fieldtype": "Section Break",
            "label": "Mongolia Tax Integration",
            "collapsible": 1
        },
        {
            "fieldname": "custom_tin",
            "fieldtype": "Data",
            "label": "TIN (ТИН)",
            "description": "Taxpayer Identification Number from MTA"
        },
        {
            "fieldname": "custom_ent_id",
            "fieldtype": "Data",
            "label": "MTA Entity ID",
            "description": "Entity ID from Tax Authority database",
            "read_only": 1
        },
        
        # eBarimt fields
        {
            "fieldname": "ebarimt_section",
            "fieldtype": "Section Break",
            "label": "eBarimt Configuration"
        },
        {
            "fieldname": "custom_merchant_tin",
            "fieldtype": "Data",
            "label": "Merchant TIN",
            "description": "eBarimt merchant TIN"
        },
        {
            "fieldname": "custom_operator_tin",
            "fieldtype": "Data",
            "label": "Operator TIN",
            "description": "eBarimt operator TIN"
        },
        {
            "fieldname": "custom_pos_no",
            "fieldtype": "Data",
            "label": "POS Number",
            "description": "eBarimt POS terminal number"
        },
        {
            "fieldname": "custom_district_code",
            "fieldtype": "Link",
            "options": "eBarimt District",
            "label": "District Code",
            "description": "Default district for receipts"
        }
    ]
}
```

### Phase 3: Implement "Read from Company" Pattern

Each app implements a helper to get org info:

```python
# etax/utils/company.py

import frappe

def get_org_info(settings):
    """
    Get organization info, preferring Company if linked.
    
    Returns:
        dict: {
            'org_regno': str,  # PIN
            'org_name': str,
            'taxpayer_tin': str,  # TIN
            'ent_id': str
        }
    """
    # If Company is linked and has data, use it
    if settings.company:
        company = frappe.get_cached_doc("Company", settings.company)
        
        # Check if Company has the required fields
        if company.tax_id:  # PIN is in tax_id field
            return {
                'org_regno': company.tax_id,
                'org_name': company.company_name,
                'taxpayer_tin': company.get('custom_tin') or settings.taxpayer_tin,
                'ent_id': company.get('custom_ent_id') or settings.ent_id
            }
    
    # Fallback to Settings fields
    return {
        'org_regno': settings.org_regno,
        'org_name': settings.org_name,
        'taxpayer_tin': settings.taxpayer_tin,
        'ent_id': settings.ent_id
    }
```

```python
# ebarimt/utils/company.py

import frappe

def get_merchant_info(settings):
    """
    Get merchant info, preferring Company if linked.
    
    Returns:
        dict: {
            'merchant_tin': str,
            'operator_tin': str,
            'pos_no': str,
            'district_code': str
        }
    """
    # If Company is linked and has data, use it
    if settings.get('company'):
        company = frappe.get_cached_doc("Company", settings.company)
        
        if company.get('custom_merchant_tin'):
            return {
                'merchant_tin': company.custom_merchant_tin,
                'operator_tin': company.get('custom_operator_tin') or settings.operator_tin,
                'pos_no': company.get('custom_pos_no') or settings.pos_no,
                'district_code': company.get('custom_district_code') or settings.district_code
            }
    
    # Fallback to Settings fields
    return {
        'merchant_tin': settings.merchant_tin,
        'operator_tin': settings.operator_tin,
        'pos_no': settings.pos_no,
        'district_code': settings.district_code
    }
```

---

## Data Flow Diagrams

### Scenario 1: Standalone App (No ERPNext)

```
┌─────────────────────────────────────────────────────────────────┐
│                     STANDALONE MODE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User enters org info directly in App Settings:                 │
│                                                                 │
│  eTax Settings                                                  │
│  ├─ company: (empty)          ← No Company link                 │
│  ├─ org_regno: "6709389"      ← User enters manually            │
│  ├─ taxpayer_tin: "152..."    ← Fetched from eTax API           │
│  └─ ent_id: "10741903"        ← Fetched from eTax API           │
│                                                                 │
│  App uses Settings fields directly                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Scenario 2: ERPNext Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     ERPNEXT INTEGRATION MODE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Company: "Wind Power LLC"                                      │
│  ├─ tax_id: "6709389"         ← PIN (Registry Number)           │
│  ├─ custom_tin: "15200005097" ← TIN (from eTax sync)            │
│  ├─ custom_merchant_tin       ← From eBarimt setup              │
│  ├─ custom_operator_tin       ← From eBarimt setup              │
│  └─ custom_pos_no             ← From eBarimt setup              │
│                   │                                             │
│                   │ Linked by                                   │
│                   ▼                                             │
│  eTax Settings                                                  │
│  ├─ company: "Wind Power LLC" ← Links to Company                │
│  ├─ org_regno: (read from Company.tax_id)                       │
│  ├─ taxpayer_tin: (read from Company.custom_tin)                │
│  └─ username, password, API settings (own fields)               │
│                                                                 │
│  get_org_info() returns data from Company                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Scenario 3: Multi-Company Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                     MULTI-COMPANY MODE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Company A: "Wind Power LLC"     Company B: "Solar Energy LLC"  │
│  ├─ tax_id: "6709389"            ├─ tax_id: "1234567"           │
│  ├─ custom_tin: "152..."         ├─ custom_tin: "987..."        │
│  └─ custom_merchant_tin          └─ custom_merchant_tin         │
│           │                               │                     │
│           │                               │                     │
│           ▼                               ▼                     │
│  eTax Settings A                 eTax Settings B                │
│  (Separate settings per company - requires DocType change)      │
│                                                                 │
│  OR: Single Settings with Company selector in forms             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Field Mapping Reference

### Company ↔ App Settings Field Mapping

| ERPNext Company Field | eTax | eBarimt | eBalance | QPay |
|-----------------------|------|---------|----------|------|
| `tax_id` (PIN) | `org_regno` | - | `org_regno` | - |
| `company_name` | `org_name` | - | - | - |
| `custom_tin` | `taxpayer_tin` | - | - | - |
| `custom_ent_id` | `ent_id` | - | - | - |
| `custom_merchant_tin` | - | `merchant_tin` | - | - |
| `custom_operator_tin` | - | `operator_tin` | - | - |
| `custom_pos_no` | - | `pos_no` | - | - |
| `custom_district_code` | - | `district_code` | - | `ebarimt_default_district_code` |

### Customer ↔ Taxpayer Field Mapping

| ERPNext Customer Field | eBarimt | eTax | Purpose |
|------------------------|---------|------|---------|
| `custom_tin` | `customerTin` | `tin` | Tax identification |
| `custom_regno` | `regNo` lookup | `pin` | Registry number |
| `custom_vat_payer` | `vatPayer` | - | VAT status |
| `custom_city_payer` | `cityPayer` | - | City tax status |
| `custom_taxpayer_name` | `name` | `entityName` | Official name |
| `ebarimt_type` | `billType` selector | - | B2C/B2B |

---

## Implementation Checklist

### For Each App:

- [ ] Add `company` Link field to Settings DocType
- [ ] Create `utils/company.py` with helper functions
- [ ] Update API client to use helper functions
- [ ] Update `test_connection` to save data to Company (if linked)
- [ ] Add "Sync to Company" button in Settings form
- [ ] Update documentation

### For ERPNext:

- [ ] Add custom fields to Company DocType
- [ ] Add custom fields to Customer DocType  
- [ ] Add custom fields to Supplier DocType
- [ ] Create fixtures for custom fields

### Shared:

- [ ] Create shared utility app or module
- [ ] Document field mappings
- [ ] Create data migration script for existing setups

---

## Example Implementation

### eTax Settings - Updated Controller

```python
# etax/etax/doctype/etax_settings/etax_settings.py

import frappe
from frappe.model.document import Document

class ETaxSettings(Document):
    def get_org_regno(self):
        """Get organization registry number (PIN)"""
        if self.company:
            company = frappe.get_cached_doc("Company", self.company)
            if company.tax_id:
                return company.tax_id
        return self.org_regno
    
    def get_taxpayer_tin(self):
        """Get taxpayer TIN"""
        if self.company:
            company = frappe.get_cached_doc("Company", self.company)
            if company.get('custom_tin'):
                return company.custom_tin
        return self.taxpayer_tin
    
    @frappe.whitelist()
    def test_connection(self):
        """Test connection and optionally sync to Company"""
        from etax.api.client import ETaxClient
        
        client = ETaxClient(self)
        orgs = client.get_user_orgs()
        
        # Find matching org
        org_regno = self.get_org_regno()
        matching_org = None
        for org in orgs:
            if str(org.get('pin')) == str(org_regno):
                matching_org = org
                break
        
        if matching_org:
            # Update Settings
            self.org_name = matching_org.get('entityName')
            self.taxpayer_tin = matching_org.get('tin')
            self.ent_id = str(matching_org.get('id'))
            self.connection_status = "Connected"
            self.save()
            
            # Sync to Company if linked
            if self.company:
                self._sync_to_company(matching_org)
            
            return {
                "success": True,
                "message": f"Connected: {self.org_name}",
                "org": matching_org
            }
        
        return {"success": False, "message": "Organization not found"}
    
    def _sync_to_company(self, org_data):
        """Sync organization data to linked Company"""
        frappe.db.set_value("Company", self.company, {
            "tax_id": org_data.get('pin'),  # PIN
            "custom_tin": org_data.get('tin'),  # TIN
            "custom_ent_id": str(org_data.get('id'))
        }, update_modified=False)
        frappe.db.commit()
        
        frappe.msgprint(f"Synced to Company: {self.company}")
```

### eBarimt Settings - Updated Controller

```python
# ebarimt/ebarimt/doctype/ebarimt_settings/ebarimt_settings.py

import frappe
from frappe.model.document import Document

class EBarimtSettings(Document):
    def get_merchant_tin(self):
        """Get merchant TIN"""
        if self.company:
            company = frappe.get_cached_doc("Company", self.company)
            if company.get('custom_merchant_tin'):
                return company.custom_merchant_tin
        return self.merchant_tin
    
    def get_operator_tin(self):
        """Get operator TIN"""
        if self.company:
            company = frappe.get_cached_doc("Company", self.company)
            if company.get('custom_operator_tin'):
                return company.custom_operator_tin
        return self.operator_tin
    
    def get_pos_no(self):
        """Get POS number"""
        if self.company:
            company = frappe.get_cached_doc("Company", self.company)
            if company.get('custom_pos_no'):
                return company.custom_pos_no
        return self.pos_no
    
    @frappe.whitelist()
    def test_connection(self):
        """Test connection and optionally sync to Company"""
        from ebarimt.api.client import EBarimtClient
        
        client = EBarimtClient(self)
        info = client.get_info()
        
        if info:
            # Update Settings
            self.operator_name = info.get('operatorName')
            self.operator_tin = info.get('operatorTIN')
            self.left_lotteries = info.get('leftLotteries')
            self.connection_status = "Connected"
            
            # Get merchant TIN from merchants list
            merchants = info.get('merchants', [])
            if merchants:
                self.merchant_tin = merchants[0].get('tin')
            
            self.save()
            
            # Sync to Company if linked
            if self.company:
                self._sync_to_company(info)
            
            return {"success": True, "message": "Connected", "info": info}
        
        return {"success": False, "message": "Connection failed"}
    
    def _sync_to_company(self, info):
        """Sync POS info to linked Company"""
        update_fields = {
            "custom_operator_tin": info.get('operatorTIN'),
            "custom_pos_no": info.get('posNo')
        }
        
        merchants = info.get('merchants', [])
        if merchants:
            update_fields["custom_merchant_tin"] = merchants[0].get('tin')
        
        frappe.db.set_value("Company", self.company, update_fields, update_modified=False)
        frappe.db.commit()
```

---

## Summary

### Key Principles:

1. **ERPNext Company is the master record** for legal entity info
2. **Apps read from Company** when linked, fallback to own Settings
3. **Apps remain independent** - can work without Company link
4. **Sync is bi-directional** - fetch from API → save to Company
5. **Customer/Supplier** also link to external taxpayer data

### Benefits:

1. **Single Source of Truth** - Company holds all tax identifiers
2. **No Duplication** - Each identifier stored once
3. **Consistency** - All apps see same data
4. **Flexibility** - Works with or without ERPNext
5. **Multi-Company** - Can support multiple companies

### Next Steps:

1. Add `company` field to each app's Settings
2. Add custom fields to Company DocType
3. Implement `get_*` helper methods
4. Update `test_connection` to sync to Company
5. Test all scenarios (standalone, integrated, multi-company)
