# eTax - Mongolian Electronic Tax Reporting System for ERPNext

[![Frappe](https://img.shields.io/badge/Frappe-v15-blue)](https://frappeframework.com)
[![ERPNext](https://img.shields.io/badge/ERPNext-v15-blue)](https://erpnext.com)
[![License](https://img.shields.io/badge/License-GPL--3.0-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.3.0-brightgreen)](https://github.com/mn-frappe/etax)

Full integration with Mongolia's eTax (etax.mta.mn) electronic tax reporting system for ERPNext v15.

## 🎯 Overview

eTax is Mongolia's mandatory electronic tax filing system operated by the Mongolian Tax Authority (MTA). This app provides:

- **100% API Coverage** - All 14 eTax API endpoints implemented
- **Multi-Entity Support** - Handle multiple taxpayer entities/organizations
- **ERPNext Integration** - Auto-generate tax reports from ERPNext data
- **Performance Optimized** - Connection pooling, response caching, lazy loading
- **Batch Operations** - Submit multiple reports efficiently

## 🚀 Key Features

### eTax API v1 (14/14 Endpoints)

| Category | Count | Description |
|----------|-------|-------------|
| User/Org | 1 | Get user organizations |
| Tax Reports | 8 | List, history, forms, data, save, submit |
| Sheets | 5 | Attachments and supporting documents |

### ERPNext DocType Integration

| DocType | Integration | Features |
|---------|-------------|----------|
| Company | ✅ Full | Multi-company, entity mapping |
| GL Entry | ✅ Full | Auto-generate tax report data |
| Sales Invoice | ✅ Full | VAT report integration |
| Purchase Invoice | ✅ Full | Input VAT tracking |
| Journal Entry | ✅ Full | Tax adjustments |

### Tax Report Types

| Report Code | Name | Frequency |
|-------------|------|-----------|
| ААНОАТ-01 | Corporate Income Tax | Annual |
| ААНОАТ-05 | CIT Quarterly Advance | Quarterly |
| НӨАТ-01 | VAT Return | Monthly |
| НӨАТ-03 | VAT Sales Ledger | Monthly |
| НӨАТ-04 | VAT Purchase Ledger | Monthly |
| ХХОАТ-01 | Personal Income Tax | Monthly |
| НД-01 | Social Insurance | Monthly |

## 📦 Installation

\`\`\`bash
# Get the app
bench get-app https://github.com/mn-frappe/etax --branch develop

# Install on your site
bench --site your-site.local install-app etax
bench --site your-site.local migrate
\`\`\`

### Dependencies

- Frappe Framework v15
- ERPNext v15 (optional, for full integration)
- Python 3.10+

## ⚙️ Configuration

### 1. eTax Settings

Go to **eTax Settings** and configure:

\`\`\`
✅ Enable eTax
🌐 API URL: https://etax.mta.mn/api
👤 Username: Your eTax username
🔑 Password: Your eTax password
🏢 Default Entity: Your primary taxpayer ID
\`\`\`

### 2. Entity Mapping

For multi-company setups, map each ERPNext Company to an eTax entity:

1. Go to **Company** > Your Company
2. Set **eTax Entity ID** field
3. Enable **Auto Submit to eTax**

### 3. Account Mapping

Map your Chart of Accounts to eTax report line items:

1. Go to **eTax Settings** > Account Mapping
2. Link GL accounts to tax report codes
3. Configure aggregation rules

## 🎯 Quick Start

### Get Available Organizations

\`\`\`python
from etax.api.client import ETaxClient

client = ETaxClient()
orgs = client.get_user_orgs()
# Returns list of entities user can file for
\`\`\`

### Get Pending Tax Reports

\`\`\`python
# Get reports due for filing
reports = client.get_report_list(entity_id="1234567")
for report in reports:
    print(f"{report['form_code']}: Due {report['due_date']}")
\`\`\`

### Submit Tax Report

\`\`\`python
# Get form structure
form = client.get_form_detail(form_code="NUAT-01", year=2024, period=12)

# Prepare data
report_data = {
    "form_code": "NUAT-01",
    "year": 2024,
    "period": 12,
    "data": {...}  # Form data
}

# Save draft
client.save_form_data(report_data)

# Submit final
result = client.submit_report(report_data)
print(f"Submitted: {result['receipt_no']}")
\`\`\`

### Auto-Generate from ERPNext

\`\`\`python
from etax.api.transformer import generate_vat_report

# Generate VAT report from GL entries
report = generate_vat_report(
    company="My Company",
    year=2024,
    month=12
)

# Submit to eTax
client.submit_report(report)
\`\`\`

## 📊 DocTypes

| DocType | Description |
|---------|-------------|
| eTax Settings | Global configuration and credentials |
| eTax Report | Tax report header and status |
| eTax Report Data Item | Report line items |
| eTax Submission Log | API call history and audit trail |
| eTax Taxpayer | Cached taxpayer/entity information |
| eTax Report Form | Form template definitions |
| eTax Sheet Form | Attachment sheet templates |

## 🔌 API Reference

### User/Organization

| Method | Description |
|--------|-------------|
| \`get_user_orgs()\` | Get list of organizations user can file for |

### Tax Report Operations

| Method | Description |
|--------|-------------|
| \`get_report_list(ent_id)\` | Get pending reports |
| \`get_report_history(ent_id, year)\` | Get submitted report history |
| \`get_late_list(ent_id)\` | Get overdue reports |
| \`get_form_list(ent_id, tax_type)\` | Get available form templates |
| \`get_form_detail(form_code, year, period)\` | Get form structure/schema |
| \`get_form_data(report_id)\` | Get saved report data |
| \`save_form_data(data)\` | Save report as draft |
| \`submit_report(data)\` | Submit report (final) |

### Sheet/Attachment Operations

| Method | Description |
|--------|-------------|
| \`get_sheet_list(report_id)\` | Get attachment sheets |
| \`get_sheet_detail(sheet_id)\` | Get sheet structure |
| \`get_sheet_data(sheet_id)\` | Get sheet data |
| \`save_sheet_data(data)\` | Save sheet data |
| \`delete_all_sheet_data(report_id)\` | Clear all sheet data |

## 🔗 Related Apps

| App | Description |
|-----|-------------|
| [QPay](https://github.com/mn-frappe/qpay) | QPay payment gateway integration |
| [eBarimt](https://github.com/mn-frappe/ebarimt) | VAT receipt system integration |
| [eBalance](https://github.com/mn-frappe/ebalance) | MOF financial reporting |

All MN apps share:
- Common entity management (\`mn_entity.py\`)
- Unified API gateway (api.frappe.mn)
- Consistent ERPNext integration patterns

## 🧪 Testing

\`\`\`bash
# Run all tests
bench --site your-site.local run-tests --app etax

# Run specific test
bench --site your-site.local run-tests --app etax --module etax.tests.test_client

# Test coverage
bench --site your-site.local run-tests --app etax --coverage
\`\`\`

## 📁 Project Structure

\`\`\`
etax/
├── etax/
│   ├── api/
│   │   ├── client.py        # Main API client (14 endpoints)
│   │   ├── auth.py          # OAuth2 authentication
│   │   ├── http_client.py   # HTTP with connection pooling
│   │   ├── cache.py         # Redis response caching
│   │   ├── transformer.py   # ERPNext → eTax data transform
│   │   └── batch.py         # Bulk operations
│   ├── etax/
│   │   └── doctype/
│   │       ├── etax_settings/
│   │       ├── etax_report/
│   │       ├── etax_submission_log/
│   │       └── etax_taxpayer/
│   ├── setup/
│   │   └── install.py       # Post-install setup
│   ├── tests/               # Test suite
│   └── mn_entity.py         # Multi-entity support
├── hooks.py
└── pyproject.toml
\`\`\`

## 📝 Changelog

### v1.3.0 (Current)
- Multi-entity support for multiple taxpayer organizations
- Connection pooling and response caching
- Enhanced ERPNext app compatibility
- Comprehensive test suite

### v1.2.0
- Full eTax API implementation (14 endpoints)
- ERPNext GL Entry integration
- Batch submission support

### v1.1.0
- OAuth2 authentication
- Basic report submission

### v1.0.0
- Initial release
- Basic API client

## 🤝 Contributing

1. Fork the repository
2. Install pre-commit: \`pre-commit install\`
3. Run tests: \`bench run-tests --app etax\`
4. Submit PR

### Code Quality Tools

- **ruff** - Python linting and formatting
- **eslint** - JavaScript linting
- **prettier** - Code formatting
- **pyupgrade** - Python syntax upgrades

## 📄 License

GNU General Public License v3.0

## 🔗 Links

- [eTax Official](https://etax.mta.mn/)
- [Mongolian Tax Authority](https://mta.mn/)
- [Report Issues](https://github.com/mn-frappe/etax/issues)

---

Developed by [mn-frappe](https://github.com/mn-frappe) for the Mongolian ERPNext community 🇲🇳
