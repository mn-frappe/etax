# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eTax - Mongolia Tax Authority Integration for ERPNext

Integrates with General Department of Taxation (ТЕГ) for:
- VAT Reports (НӨАТ тайлан)
- Corporate Income Tax (ААНОАТ)
- Personal Income Tax (ХАОАТ)
- Withholding Tax (Татвар суутгал)

100% Integration Coverage:
- VAT sales/purchase invoice processing
- TIN validation and taxpayer lookup
- Automated tax report generation
- Tax authority submission workflow

100% API Endpoint Coverage (14/14):
- getUserOrgs, getList, getHistory, getLateList
- getFormList, getFormDetail, getFormData, saveFormData, submit
- getSheetList, getSheetDetail, getSheetData, saveSheetData, deleteAllSheetData

100% Digital Signature Workflow:
- HMAC-SHA256 signature generation
- NE-KEY API authentication
- Report payload hashing and verification
- Signature audit logging

Features (v1.3.0):
- Comprehensive logging utilities (logger.py)
- Multi-level approval workflow for report submissions
- VAT data caching and pre-aggregation
- Multi-company entity support
- Digital signature module (signature.py)
"""

__version__ = "1.5.0"
