# Mongolian Government Integration Apps - Detailed API & Data Reference

## Overview

This document provides detailed information about all 4 Mongolian government integration apps:
- **eTax** - Tax Authority (MTA) integration for tax returns
- **eBarimt** - VAT receipt system
- **eBalance** - Ministry of Finance financial reporting
- **QPay** - Payment gateway with eBarimt integration

---

## 1. eTax App

### 1.1 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vatps/user/getUserOrgs` | GET | Get user's organizations |
| `/api/vatps/taxpayer/getReportList` | GET | Get tax report list |
| `/api/vatps/taxpayer/getLateReports` | GET | Get overdue reports |
| `/api/vatps/taxpayer/getFormList` | GET | Get form types |
| `/api/vatps/taxpayer/getFormDetail` | GET | Get form details |
| `/api/vatps/taxpayer/getSheetList` | GET | Get report sheets |
| `/api/vatps/taxpayer/getSheetData` | GET | Get sheet data |
| `/api/vatps/taxpayer/saveSheetData` | POST | Save sheet data |
| `/api/vatps/taxpayer/submitReport` | POST | Submit tax report |

### 1.2 API Response: getUserOrgs

```json
{
  "id": 10178918,
  "tin": "98100787027",
  "pin": "6283888",
  "entityName": "Мон эксчэйнж Ай Өү",
  "entType": 2,
  "entStatus": 2,
  "isConfirmed": 1,
  "confirmedDate": "2018-07-24 08:59:16",
  "taxRegDate": "2018-07-24 08:59:16",
  "recordSource": 3,
  "parentId": null,
  "refEntType": {
    "id": 2,
    "code": "Organization",
    "name": "Хуулийн этгээд"
  },
  "refEntStatus": {
    "id": 2,
    "code": "REG",
    "name": "Бүртгэгдсэн",
    "isTaxType": 1
  },
  "taxpayerBranchView": {
    "tin": "98100787027",
    "entId": 10178918,
    "pin": "6283888",
    "legalName": "Мон эксчэйнж Ай Өү",
    "branchId": 29,
    "branchCode": "23",
    "branchName": "Хан-Уул",
    "subBranchId": 143,
    "subBranchName": "3-р хороо",
    "subBranchCode": "2303",
    "legalStatusId": 27,
    "legalStatusCode": "11",
    "legalStatusName": "Хязгаарлагдмал хариуцлагатай компани",
    "entStatusId": 2,
    "entStatusName": "Бүртгэгдсэн"
  },
  "agreeGeneralRoleUser": true,
  "ebarimtLogin": true
}
```

### 1.3 Key Identifiers

| Field | Description | Example |
|-------|-------------|---------|
| `id` | Entity ID in MTA database | 10178918 |
| `tin` | Taxpayer Identification Number (TIN) | 98100787027 |
| `pin` | Registration Number (Company Registry) | 6283888 |
| `entType` | Entity Type (1=Individual, 2=Legal Entity) | 2 |
| `branchCode` | Tax office branch code | 23 |
| `subBranchCode` | Tax office sub-branch code | 2303 |

### 1.4 DocType: eTax Settings

| Field | Type | Description |
|-------|------|-------------|
| `environment` | Select | Staging/Production |
| `enabled` | Check | Enable eTax integration |
| `username` | Data | MTA login username |
| `password` | Password | MTA login password |
| `ne_key` | Password | NE signing key (optional) |
| `org_regno` | Data | Organization registry number (PIN) |
| `connection_status` | Data | Connected/Disconnected |
| `org_name` | Data | Organization name (auto-filled) |
| `taxpayer_tin` | Data | TIN (auto-filled) |
| `taxpayer_type` | Select | 1-Individual, 2-Legal Entity |
| `ent_id` | Data | Entity ID from MTA |

### 1.5 DocType: eTax Report

| Field | Type | Description |
|-------|------|-------------|
| `report_no` | Int | Report number in sequence |
| `report_id` | Data | Unique report ID from MTA |
| `tax_report_code` | Data | Tax type code |
| `status` | Select | New/Submitted/Assigned/Returned/Received |
| `tax_type_id` | Int | Tax type identifier |
| `tax_type_code` | Data | Tax type code (e.g., "VAT", "CIT") |
| `tax_type_name` | Data | Tax type name in Mongolian |
| `period_year` | Int | Tax year |
| `period` | Int | Period number (month/quarter) |
| `return_begin_date` | Date | Period start date |
| `return_due_date` | Date | Filing deadline |
| `branch_code` | Data | Tax office branch |
| `ent_id` | Int | Entity ID |
| `pin` | Data | Registry number |

### 1.6 DocType: eTax Taxpayer

| Field | Type | Description |
|-------|------|-------------|
| `tin` | Data* | TIN (required, unique) |
| `pin` | Data | Registry Number |
| `entity_name` | Data | Legal name |
| `ent_type` | Int | 1=Individual, 2=Legal Entity |
| `ent_status` | Int | Status code |
| `branch_code` | Data | Tax office branch |
| `ebarimt_login` | Check | Has eBarimt access |

---

## 2. eBarimt App

### 2.1 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rest/info` | GET | POS terminal info |
| `/rest/receipt` | POST | Create VAT receipt |
| `/rest/receipt/{id}` | GET | Get receipt info |
| `/rest/receipt` | DELETE | Void receipt |
| `/api/info/check/getInfo` | GET | Lookup taxpayer by TIN |
| `/api/info/check/getTinInfo` | GET | Get TIN from registry number |
| `/api/info/check/getBranchInfo` | GET | Get district codes |
| `/api/receipt/receipt/getProductTaxCode` | GET | Get tax product codes |
| `/api/info/check/barcode/v2` | GET | BUNA classification lookup |

### 2.2 API Response: POS Info (/rest/info)

```json
{
  "operatorName": "TEST OPERATOR 1",
  "operatorTIN": "23354214778",
  "posId": 101320638,
  "posNo": "10011702",
  "version": "3.2.16",
  "lastSentDate": "2025-12-17 11:08:21",
  "leftLotteries": 19962,
  "paymentTypes": [
    {"code": "CASH", "name": "Бэлэнээр"},
    {"code": "PAYMENT_CARD", "name": "Төлбөрийн карт"},
    {"code": "BANK_TRANSFER", "name": "Банкны шилжүүлэг"},
    {"code": "EMD", "name": "Эрүүл мэндийн даатгалаар"}
  ],
  "merchants": [
    {
      "tin": "37900846788",
      "name": "ТЕСТИЙН ХЭРЭГЛЭГЧ 1",
      "vatPayer": true,
      "customers": [
        {"tin": "37900846788", "name": "ТЕСТИЙН ХЭРЭГЛЭГЧ 1", "vatPayer": true},
        {"tin": "10000000000", "name": "ЭЦСИЙН ХЭРЭГЛЭГЧ", "vatPayer": false}
      ]
    }
  ]
}
```

### 2.3 API Response: Taxpayer Info

```json
{
  "tin": "6283888",
  "name": "Мон эксчэйнж Ай Өү",
  "vatPayer": true,
  "cityPayer": false,
  "lastReceiptDate": "2024-01-15"
}
```

### 2.4 Receipt Request Structure

```json
{
  "amount": 100000,
  "vat": 9090.91,
  "cashAmount": 100000,
  "nonCashAmount": 0,
  "cityTax": 0,
  "districtCode": "2303",
  "posNo": "10011702",
  "customerTin": "",
  "billType": "B2C_RECEIPT",
  "stocks": [
    {
      "code": "000001",
      "name": "Product Name",
      "measureUnit": "ш",
      "qty": 1,
      "unitPrice": 100000,
      "totalAmount": 100000,
      "cityTax": 0,
      "vat": 9090.91,
      "barCode": ""
    }
  ],
  "payments": [
    {"code": "CASH", "status": "PAID", "paidAmount": 100000}
  ]
}
```

### 2.5 Receipt Response Structure

```json
{
  "id": "300123456789012345678901234567890",
  "posNo": "10011702",
  "lottery": "ЦЦ12345678",
  "qrData": "...",
  "date": "2024-01-15 14:30:00",
  "billType": "B2C_RECEIPT",
  "internalId": "123456",
  "macAddress": "AA:BB:CC:DD:EE:FF"
}
```

### 2.6 Key Identifiers

| Field | Description | Example |
|-------|-------------|---------|
| `operatorTIN` | Operator's TIN | 23354214778 |
| `merchantTIN` | Merchant's TIN | 37900846788 |
| `customerTIN` | Customer's TIN (B2B) | 6283888 |
| `posNo` | POS terminal number | 10011702 |
| `districtCode` | District code (4 digits) | 2303 |
| `id` (DDTD) | 33-digit receipt ID | 300123... |

### 2.7 DocType: eBarimt Settings

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | Check | Enable eBarimt |
| `environment` | Select | Staging/Production |
| `pos_no` | Data | POS terminal number |
| `operator_tin` | Data | Operator TIN |
| `merchant_tin` | Data | Merchant TIN |
| `district_code` | Link | Default district |
| `connection_status` | Select | Connected/Disconnected/Not Configured |
| `auto_submit_receipt` | Check | Auto-submit on invoice |
| `auto_void_on_cancel` | Check | Auto-void on cancel |
| `skip_if_qpay_ebarimt` | Check | Skip if QPay handled eBarimt |

### 2.8 DocType: eBarimt Receipt Log

| Field | Type | Description |
|-------|------|-------------|
| `sales_invoice` | Link | ERPNext Sales Invoice |
| `pos_invoice` | Link | ERPNext POS Invoice |
| `status` | Select | Pending/Success/Failed/Voided |
| `bill_type` | Select | B2C_RECEIPT/B2B_RECEIPT |
| `receipt_id` | Data | 33-digit DDTD |
| `lottery_number` | Data | Lottery code |
| `total_amount` | Currency | Receipt total |
| `vat_amount` | Currency | VAT amount |
| `city_tax` | Currency | City tax |
| `merchant_tin` | Data | Merchant TIN |
| `customer_tin` | Data | Customer TIN (B2B) |
| `district_code` | Link | District |
| `qr_data` | Small Text | QR code data |

### 2.9 DocType: eBarimt District

| Field | Type | Description |
|-------|------|-------------|
| `code` | Data* | 4-digit district code |
| `name_mn` | Data | District name (Mongolian) |
| `name_en` | Data | District name (English) |
| `aimag` | Data | Province/City |
| `sum` | Data | District/Soum |

### 2.10 DocType: eBarimt Tax Code

| Field | Type | Description |
|-------|------|-------------|
| `tax_product_code` | Data* | Tax code |
| `tax_product_name` | Small Text | Code description |
| `tax_type_code` | Int | Tax type identifier |
| `tax_type_name` | Data | VAT/VAT_FREE/VAT_ZERO/NO_VAT |
| `start_date` | Date | Effective from |
| `end_date` | Date | Effective until |

---

## 3. eBalance App

### 3.1 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tpiRequest/getWritingConfigs` | GET | Get report periods |
| `/perRole/getUserRoles` | GET | Get user roles |
| `/reportConnectConfig/getAllConfigWithReportOrgList` | GET | Get connected periods |
| `/reportConnectConfig/getReportUserOrgHdrList` | GET | Get report requests |
| `/reportConnectConfig/decideReportUserOrgHdr` | GET | Start report entry |
| `/reportData/getReportData` | GET | Get form data |
| `/reportConnectConfig/getReportPackageMap` | GET | Get form names |
| `/calculate/saveReportData` | POST | Save draft |
| `/calculate/sendReportData` | POST | Submit final |
| `/tpiRequest/getConfirmedReportData` | GET | Query confirmed reports |

### 3.2 API Response: Writing Configs (Report Periods)

```json
[
  {
    "code": "End_2024_H_2",
    "name": "2024 оны жилийн эцсийн тайлан"
  },
  {
    "code": "SubEnd_2024_M_1",
    "name": "2024 оны хагас жилийн тайлан"
  }
]
```

### 3.3 API Response: User Roles

```json
{
  "id": 12345,
  "perMapUserRoleId": 12345,
  "perRole": "Accountant",
  "userOrganization": {
    "regNo": "6283888",
    "name": "Мон эксчэйнж Ай Өү"
  }
}
```

### 3.4 Key Identifiers

| Field | Description | Example |
|-------|-------------|---------|
| `userRegNo` | User's registry number | 6283888 |
| `orgRegNo` | Organization's registry number | 6283888 |
| `perMapUserRoleId` | User role ID | 12345 |
| `writingConfigCode` | Report period code | End_2024_H_2 |
| `reportUserOrgHdrId` | Report request ID | 67890 |

### 3.5 DocType: eBalance Settings

| Field | Type | Description |
|-------|------|-------------|
| `environment` | Select | Staging/Production |
| `enabled` | Check | Enable eBalance |
| `username` | Data* | MOF login username |
| `password` | Password* | MOF login password |
| `org_regno` | Data* | Organization registry number |
| `user_regno` | Data | User registry number |
| `per_map_user_role_id` | Data | Role ID (auto-filled) |
| `connection_status` | Data | Connection status |
| `company` | Link | ERPNext Company |
| `default_fiscal_year` | Link | ERPNext Fiscal Year |

### 3.6 DocType: eBalance Report Request

| Field | Type | Description |
|-------|------|-------------|
| `report_period` | Link* | Report period |
| `report_user_org_hdr_id` | Data | MOF report ID |
| `status` | Select | Draft/Generating/Ready/In Progress/Submitted/Confirmed/Rejected/Failed |
| `company` | Link* | ERPNext Company |
| `fiscal_year` | Link | Fiscal Year |
| `from_date` | Date* | Period start |
| `to_date` | Date* | Period end |
| `balance_sheet_preview` | Code | JSON balance sheet data |
| `income_statement_preview` | Code | JSON income statement data |
| `validation_errors` | Code | JSON validation errors |

### 3.7 DocType: eBalance Report Period

| Field | Type | Description |
|-------|------|-------------|
| `period_code` | Data* | Period code (End_2024_H_2) |
| `period_name` | Data* | Period name |
| `period_type` | Select | Annual/Semi-Annual/Quarterly/Monthly |
| `fiscal_year` | Link | ERPNext Fiscal Year |
| `status` | Select | Open/Closed/Submitted |
| `is_current` | Check | Current active period |

---

## 4. QPay App

### 4.1 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/token` | POST | Get access token |
| `/invoice` | POST | Create invoice |
| `/invoice/{id}` | GET | Get invoice info |
| `/invoice/{id}` | DELETE | Cancel invoice |
| `/payment/check` | POST | Check payment status |
| `/payment/{id}` | GET | Get payment details |
| `/payment/{id}` | DELETE | Cancel payment |
| `/payment/refund` | POST | Refund payment |
| `/payment/list` | POST | List payments |
| `/ebarimt_v3/create` | POST | Create eBarimt |
| `/ebarimt_v3/{payment_id}` | DELETE | Cancel eBarimt |
| `/subscription` | POST | Create subscription |
| `/subscription/{id}` | GET/DELETE | Manage subscription |

### 4.2 Create Invoice Request

```json
{
  "invoice_code": "MERCHANT_INVOICE_CODE",
  "sender_invoice_no": "INV-2024-001",
  "invoice_description": "Payment for services",
  "amount": 100000,
  "callback_url": "https://yoursite.com/api/callback",
  
  "invoice_receiver_code": "CUSTOMER_CODE",
  "invoice_receiver_data": {
    "register": "6283888",
    "name": "Customer Name",
    "email": "customer@email.com",
    "phone": "99001234"
  },
  
  "sender_branch_code": "2303",
  "sender_staff_code": "EMP001",
  
  "enable_expiry": true,
  "expiry_date": "2024-01-20 23:59:59",
  
  "allow_partial": true,
  "minimum_amount": 50000,
  
  "allow_exceed": false,
  "maximum_amount": 100000,
  
  "lines": [
    {
      "line_description": "Service Fee",
      "line_quantity": "1",
      "line_unit_price": "100000",
      "tax_product_code": "0"
    }
  ]
}
```

### 4.3 Invoice Response

```json
{
  "invoice_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "qr_text": "...",
  "qr_image": "data:image/png;base64,...",
  "qpay_short_url": "https://qr.qpay.mn/abc123",
  "urls": [
    {"name": "Khan Bank", "logo": "...", "link": "khanbank://..."},
    {"name": "Golomt Bank", "logo": "...", "link": "golomt://..."}
  ]
}
```

### 4.4 Payment Check Response

```json
{
  "count": 1,
  "paid_amount": 100000,
  "rows": [
    {
      "payment_id": "p1a2b3c4d5",
      "payment_status": "PAID",
      "payment_amount": 100000,
      "payment_currency": "MNT",
      "payment_wallet": "Khan Bank",
      "payment_type": "P2P",
      "transaction_id": "TXN123456",
      "payment_date": "2024-01-15 14:30:00"
    }
  ]
}
```

### 4.5 eBarimt Create Request

```json
{
  "payment_id": "p1a2b3c4d5",
  "ebarimt_receiver_type": "CITIZEN",
  "ebarimt_receiver": "99001234",
  "register_no": "6283888",
  "customer_tin": "98100787027",
  "customer_name": "Customer Name",
  "lines": [
    {
      "line_description": "Service Fee",
      "line_quantity": "1",
      "line_unit_price": "100000",
      "tax_product_code": "0",
      "tax_code": null,
      "discounts": [],
      "surcharges": [],
      "taxes": []
    }
  ]
}
```

### 4.6 Key Identifiers

| Field | Description | Example |
|-------|-------------|---------|
| `invoice_code` | Merchant invoice template | QPAY_MERCHANT_001 |
| `sender_invoice_no` | Your internal invoice number | INV-2024-001 |
| `invoice_id` | QPay invoice UUID | a1b2c3d4-... |
| `payment_id` | QPay payment ID | p1a2b3c4d5 |
| `sender_branch_code` | District code for eBarimt | 2303 |

### 4.7 DocType: QPay Settings

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | Check | Enable QPay |
| `environment` | Select | Sandbox/Production |
| `username` | Data* | QPay merchant username |
| `password` | Password* | QPay merchant password |
| `invoice_code` | Data* | Invoice template code |
| `ebarimt_enabled` | Check | Enable eBarimt via QPay |
| `ebarimt_auto_create` | Check | Auto-create eBarimt on payment |
| `ebarimt_default_receiver_type` | Select | Individual/Business |
| `ebarimt_default_district_code` | Link | Default district |
| `callback_url` | Data | Payment callback URL |
| `allow_partial_payment` | Check | Allow partial payments |
| `subscription_enabled` | Check | Enable subscriptions |

### 4.8 DocType: QPay Invoice

| Field | Type | Description |
|-------|------|-------------|
| `invoice_id` | Data | QPay invoice UUID |
| `sender_invoice_no` | Data | Internal invoice number |
| `status` | Select | Draft/Pending/Paid/Partially Paid/Cancelled/Expired/Refunded |
| `amount` | Currency* | Invoice amount |
| `paid_amount` | Currency | Amount paid |
| `description` | Small Text | Invoice description |
| `reference_doctype` | Link | ERPNext DocType |
| `reference_name` | Dynamic Link | ERPNext document name |
| `callback_url` | Data | Callback URL |
| `qr_image` | Long Text | Base64 QR image |
| `qpay_short_url` | Data | Short URL for payment |
| `payment_id` | Data | QPay payment ID |
| `payment_status` | Data | Payment status |
| `ebarimt_created` | Check | eBarimt created |
| `ebarimt_id` | Data | eBarimt ID |
| `ebarimt_lottery` | Data | eBarimt lottery number |
| `receiver_register` | Data | Customer registry |
| `receiver_name` | Data | Customer name |
| `sender_branch_code` | Data | District code |

---

## 5. ERPNext Integration Points

### 5.1 Company Custom Fields

| Field | Type | Used By |
|-------|------|---------|
| `tax_id` | Data | All apps - Company Registry Number (PIN) |
| `custom_merchant_tin` | Data | eBarimt - Merchant TIN |
| `custom_operator_tin` | Data | eBarimt - Operator TIN |
| `custom_pos_no` | Data | eBarimt - POS Number |
| `ebalance_enabled` | Check | eBalance - Integration enabled |
| `ebalance_org_id` | Data | eBalance - Organization ID |

### 5.2 Customer Custom Fields

| Field | Type | Used By |
|-------|------|---------|
| `custom_tin` | Data | All apps - Customer TIN |
| `custom_regno` | Data | All apps - Registry Number |
| `ebarimt_type` | Select | eBarimt - CITIZEN/COMPANY |
| `ebarimt_register` | Data | eBarimt - Phone/Register for lottery |
| `custom_vat_payer` | Check | eBarimt, eTax - VAT payer status |
| `custom_city_payer` | Check | eBarimt - City tax payer |
| `custom_taxpayer_name` | Data | All apps - Official name from MTA |
| `custom_taxpayer_synced` | Check | Track if synced with MTA |

### 5.3 Supplier Custom Fields (Recommended)

| Field | Type | Recommended For |
|-------|------|-----------------|
| `tax_id` | Data | All apps - Supplier Registry Number |
| `custom_tin` | Data | eBarimt, eTax - Supplier TIN |
| `custom_vat_payer` | Check | eBarimt - VAT payer status |

---

## 6. Common Data Mappings

### 6.1 Registry Number (PIN) Usage

| App | Field Name | API Field |
|-----|------------|-----------|
| eTax | `org_regno` | `pin` |
| eBarimt | `customerTin` lookup | `regNo` |
| eBalance | `org_regno` | `orgRegNo` |
| QPay | `receiver_register` | `register_no` |
| ERPNext | `tax_id` | - |

### 6.2 TIN Usage

| App | Field Name | API Field |
|-----|------------|-----------|
| eTax | `taxpayer_tin` | `tin` |
| eBarimt | `merchant_tin`, `customer_tin` | `tin` |
| eBalance | N/A | N/A |
| QPay | `customer_tin` | `customer_tin` |
| ERPNext | `custom_tin` | - |

### 6.3 District Code Usage

| App | Field Name | Format |
|-----|------------|--------|
| eBarimt | `district_code` | 4-digit (2303) |
| QPay | `sender_branch_code` | 4-digit (2303) |
| eTax | `sub_branch_code` | 4-digit (2303) |

---

## 7. Data Flow Patterns

### 7.1 Customer TIN Lookup Flow

```
User enters registry number (PIN)
    ↓
eBarimt API: /api/info/check/getTinInfo?regNo=6283888
    ↓
Returns TIN: 98100787027
    ↓
eBarimt API: /api/info/check/getInfo?tin=98100787027
    ↓
Returns: {name, vatPayer, cityPayer}
    ↓
Save to ERPNext Customer:
  - custom_regno = 6283888
  - custom_tin = 98100787027
  - custom_taxpayer_name = "Мон эксчэйнж Ай Өү"
  - custom_vat_payer = true
  - ebarimt_type = "COMPANY"
```

### 7.2 eBarimt Receipt Flow

```
Sales Invoice submitted
    ↓
Check customer.ebarimt_type
    ↓
If COMPANY:
  - bill_type = B2B_RECEIPT
  - customer_tin = customer.custom_tin
Else:
  - bill_type = B2C_RECEIPT
  - customer_tin = "" (empty)
    ↓
Get district_code from:
  1. Customer address → district lookup
  2. OR company.custom_pos_no settings
    ↓
Create receipt via /rest/receipt
    ↓
Store in eBarimt Receipt Log
```

### 7.3 QPay with eBarimt Flow

```
QPay Invoice created
    ↓
Customer pays via bank app
    ↓
QPay callback received
    ↓
If ebarimt_enabled:
  QPay API: /ebarimt_v3/create
    - payment_id = payment.payment_id
    - receiver_type = CITIZEN or COMPANY
    - register_no = customer.custom_regno
    ↓
  QPay returns ebarimt details
    ↓
  Update QPay Invoice:
    - ebarimt_created = true
    - ebarimt_lottery = response.lottery
```

---

## 8. Environment Configuration

### 8.1 Staging/Test URLs

| App | Auth URL | API URL |
|-----|----------|---------|
| eTax | `https://api.frappe.mn/auth/itc-staging/` | `https://api.frappe.mn/vatps-staging/` |
| eBarimt | `https://api.frappe.mn/auth/itc-staging/` | `https://api.frappe.mn/ebarimt-staging/` |
| eBalance | `https://api.frappe.mn/auth/ebalance-staging/` | `https://api.frappe.mn/ebalance-staging/` |
| QPay | `https://merchant-sandbox.qpay.mn/v2/` | `https://merchant-sandbox.qpay.mn/v2/` |

### 8.2 Production URLs

| App | Auth URL | API URL |
|-----|----------|---------|
| eTax | `https://api.frappe.mn/auth/itc/` | `https://api.frappe.mn/vatps/` |
| eBarimt | `https://api.frappe.mn/auth/itc/` | `https://api.frappe.mn/ebarimt-prod/` |
| eBalance | `https://api.frappe.mn/auth/ebalance/` | `https://api.frappe.mn/ebalance-prod/` |
| QPay | `https://merchant.qpay.mn/v2/` | `https://merchant.qpay.mn/v2/` |

---

## 9. Quick Reference

### 9.1 Taxpayer Types

| Code | Name (MN) | Name (EN) |
|------|-----------|-----------|
| 1 | Иргэн | Individual |
| 2 | Хуулийн этгээд | Legal Entity |

### 9.2 eBarimt Bill Types

| Code | Description |
|------|-------------|
| B2C_RECEIPT | Business to Consumer (lottery eligible) |
| B2B_RECEIPT | Business to Business (no lottery) |

### 9.3 VAT Tax Types

| Code | Name |
|------|------|
| VAT | Standard VAT (10%) |
| VAT_FREE | VAT Exempt |
| VAT_ZERO | Zero-rated VAT |
| NO_VAT | Non-VAT item |

### 9.4 Payment Types (eBarimt)

| Code | Name (MN) |
|------|-----------|
| CASH | Бэлэнээр |
| PAYMENT_CARD | Төлбөрийн карт |
| BANK_TRANSFER | Банкны шилжүүлэг |
| MOBILE | Мобайл |
| EMD | Эрүүл мэндийн даатгалаар |
