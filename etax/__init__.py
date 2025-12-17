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

Features (v1.2.0):
- Comprehensive logging utilities (logger.py)
- Autopilot mode for auto-sync and auto-submit reports
- VAT data caching and pre-aggregation
- Multi-company entity support
"""

__version__ = "1.2.0"
