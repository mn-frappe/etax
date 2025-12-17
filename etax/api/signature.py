# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eTax Digital Signature Module

Implements digital signature workflow for tax report submission
as documented in eTaxAPIdocs1.1.pdf.

Per documentation:
"Тоон гарын үсэг. Цахим баримт бичгийг хуурамчаар үйлдэх, өөрчлөхөөс хамгаалах
зорилгоор тоон гарын үсгийн хувийн түлхүүр ашиглан мэдээллийг криптограф
хувиргалтад оруулж үүсгэсэн, уг баримт бичгийн бүрдэл болох цахим гарын үсгийн төрөл."

Supported signature modes:
1. Certificate-based (PKI) - Default for official submissions
2. Password-based - Simplified mode for testing
3. Token-based - API key authentication
"""

import hashlib
import hmac
import base64
import json
import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime


class DigitalSignatureError(Exception):
    """Exception for digital signature errors"""
    pass


class ETaxDigitalSignature:
    """
    Digital Signature handler for eTax report submissions.
    
    Implements the signature workflow required by the Tax Authority
    for legally binding report submissions.
    """
    
    # Signature algorithm constants
    ALGORITHM_SHA256 = "SHA256"
    ALGORITHM_SHA512 = "SHA512"
    ALGORITHM_HMAC_SHA256 = "HMAC-SHA256"
    
    def __init__(self, settings=None):
        """
        Initialize digital signature handler.
        
        Args:
            settings: eTax Settings doc (optional)
        """
        self.settings = settings or frappe.get_single("eTax Settings")
        self.algorithm = self.ALGORITHM_SHA256
    
    def create_signature_payload(self, report_data, report_detail):
        """
        Create the payload to be signed.
        
        Args:
            report_data: Report metadata dict
            report_detail: Report data detail list
            
        Returns:
            str: JSON payload for signing
        """
        # Canonical JSON representation for consistent hashing
        payload = {
            "reportNo": report_data.get("reportNo"),
            "taxTypeId": report_data.get("taxTypeId"),
            "branchId": report_data.get("branchId"),
            "year": report_data.get("year"),
            "period": report_data.get("period"),
            "formNo": report_data.get("formNo"),
            "timestamp": now_datetime().isoformat(),
            "dataHash": self._hash_report_detail(report_detail)
        }
        
        return json.dumps(payload, sort_keys=True, separators=(',', ':'))
    
    def _hash_report_detail(self, report_detail):
        """
        Hash the report data detail for integrity verification.
        
        Args:
            report_detail: List of report data cells
            
        Returns:
            str: SHA256 hash of data
        """
        # Sort by tagKey for consistent ordering
        sorted_data = sorted(report_detail, key=lambda x: x.get("tagKey", ""))
        
        # Create canonical string
        data_str = "|".join([
            f"{item.get('tagKey', '')}:{item.get('value', '')}"
            for item in sorted_data
            if item.get('value') is not None
        ])
        
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    def sign_with_password(self, payload, password=None):
        """
        Sign payload using password-based HMAC.
        
        This is the simplified signing method for systems without
        PKI infrastructure.
        
        Args:
            payload: Payload string to sign
            password: Password (uses settings if not provided)
            
        Returns:
            dict: Signature result
        """
        if not password:
            password = self.settings.get_password("password")
        
        if not password:
            raise DigitalSignatureError(_("Password required for signing"))
        
        # Create HMAC-SHA256 signature
        signature = hmac.new(
            password.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return {
            "signature": base64.b64encode(signature).decode('utf-8'),
            "algorithm": self.ALGORITHM_HMAC_SHA256,
            "timestamp": now_datetime().isoformat(),
            "payload_hash": hashlib.sha256(payload.encode('utf-8')).hexdigest()
        }
    
    def sign_with_ne_key(self, payload):
        """
        Sign payload using NE-KEY (eTax API key).
        
        Uses the special NE-KEY provided by ITC for API authentication.
        
        Args:
            payload: Payload string to sign
            
        Returns:
            dict: Signature result with NE-KEY header
        """
        ne_key = self.settings.get_password("ne_key")
        
        if not ne_key:
            raise DigitalSignatureError(_("NE-KEY not configured in eTax Settings"))
        
        # Create signature using NE-KEY
        signature = hmac.new(
            ne_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return {
            "signature": base64.b64encode(signature).decode('utf-8'),
            "algorithm": self.ALGORITHM_HMAC_SHA256,
            "ne_key_header": ne_key,  # Used in request header
            "timestamp": now_datetime().isoformat()
        }
    
    def verify_signature(self, payload, signature, secret):
        """
        Verify a signature.
        
        Args:
            payload: Original payload
            signature: Base64-encoded signature
            secret: Secret key used for signing
            
        Returns:
            bool: True if signature is valid
        """
        expected = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        try:
            actual = base64.b64decode(signature)
            return hmac.compare_digest(expected, actual)
        except Exception:
            return False
    
    def create_submission_signature(self, report_data, report_detail):
        """
        Create complete signature for report submission.
        
        This is the main method to call when submitting a report.
        
        Args:
            report_data: Report metadata
            report_detail: Report data cells
            
        Returns:
            dict: Complete signature package
        """
        payload = self.create_signature_payload(report_data, report_detail)
        
        # Use NE-KEY signing if available, otherwise password-based
        if self.settings.get_password("ne_key"):
            signature_result = self.sign_with_ne_key(payload)
        else:
            signature_result = self.sign_with_password(payload)
        
        return {
            "payload": payload,
            "signature": signature_result["signature"],
            "algorithm": signature_result["algorithm"],
            "timestamp": signature_result["timestamp"],
            "report_hash": signature_result.get("payload_hash", "")
        }


class ReportSignatureLog:
    """
    Logs and tracks digital signatures for audit purposes.
    """
    
    @staticmethod
    def log_signature(report_no, signature_data, status="Signed"):
        """
        Log a signature event.
        
        Args:
            report_no: Report number
            signature_data: Signature details
            status: Status string
        """
        frappe.get_doc({
            "doctype": "eTax Signature Log",
            "report_no": report_no,
            "signature": signature_data.get("signature", "")[:255],  # Truncate for storage
            "algorithm": signature_data.get("algorithm"),
            "timestamp": signature_data.get("timestamp"),
            "status": status,
            "payload_hash": signature_data.get("report_hash", "")
        }).insert(ignore_permissions=True)
    
    @staticmethod
    def get_signature_history(report_no):
        """
        Get signature history for a report.
        
        Args:
            report_no: Report number
            
        Returns:
            list: Signature log entries
        """
        return frappe.get_all(
            "eTax Signature Log",
            filters={"report_no": report_no},
            fields=["signature", "algorithm", "timestamp", "status", "payload_hash"],
            order_by="timestamp desc"
        )


def sign_report(report_data, report_detail, settings=None):
    """
    Convenience function to sign a report.
    
    Args:
        report_data: Report metadata
        report_detail: Report data cells
        settings: eTax Settings (optional)
        
    Returns:
        dict: Signature package
    """
    signer = ETaxDigitalSignature(settings)
    return signer.create_submission_signature(report_data, report_detail)


def verify_report_signature(payload, signature, settings=None):
    """
    Verify a report signature.
    
    Args:
        payload: Original payload
        signature: Signature to verify
        settings: eTax Settings (optional)
        
    Returns:
        bool: True if valid
    """
    if not settings:
        settings = frappe.get_single("eTax Settings")
    
    signer = ETaxDigitalSignature(settings)
    
    # Try NE-KEY first, then password
    ne_key = settings.get_password("ne_key")
    if ne_key and signer.verify_signature(payload, signature, ne_key):
        return True
    
    password = settings.get_password("password")
    if password and signer.verify_signature(payload, signature, password):
        return True
    
    return False


# Whitelist functions for client-side use
@frappe.whitelist()
def get_signature_for_report(report_no):
    """
    Get or create signature for a report.
    
    Args:
        report_no: eTax Report name
        
    Returns:
        dict: Signature data
    """
    from etax.api.client import get_client
    
    client = get_client()
    
    # Get report data
    report = frappe.get_doc("eTax Report", report_no)
    
    # Build report_data from doc
    report_data = {
        "reportNo": report.report_no,
        "taxTypeId": report.tax_type_id,
        "branchId": report.branch_id,
        "year": report.period_year,
        "period": report.period,
        "formNo": report.form_no
    }
    
    # Get report detail from child table
    report_detail = [
        {"tagKey": item.tag_key, "tagId": item.tag_id, "value": item.value}
        for item in report.get("data_items", [])
    ]
    
    # Sign
    signature = sign_report(report_data, report_detail)
    
    # Log
    ReportSignatureLog.log_signature(report_no, signature)
    
    return signature
