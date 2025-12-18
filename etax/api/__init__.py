# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax API Module

Provides API client for eTax (Electronic Tax Report System) integration.
"""

from etax.api.auth import ETaxAuth, ETaxAuthError, get_auth
from etax.api.client import ETaxClient, get_client
from etax.api.http_client import ETaxHTTPClient, ETaxHTTPError, get_http_client
from etax.api.transformer import ETaxTransformer, get_transformer

__all__ = [
    "ETaxAuth",
    "ETaxAuthError",
    "ETaxClient",
    "ETaxHTTPClient",
    "ETaxHTTPError",
    "ETaxTransformer",
    "get_auth",
    "get_client",
    "get_http_client",
    "get_transformer"
]
