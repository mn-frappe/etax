# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Comprehensive Tests for eTax Digital Signature Module

Tests digital signature workflow for tax report submission
as documented in eTaxAPIdocs1.1.pdf.
"""

import json
import hashlib
import hmac
import base64
from unittest.mock import MagicMock

import frappe
from frappe.tests.utils import FrappeTestCase

from etax.api.signature import (
    ETaxDigitalSignature,
    ReportSignatureLog,
    DigitalSignatureError,
    sign_report,
    verify_report_signature
)


class TestETaxDigitalSignature(FrappeTestCase):
    """Tests for ETaxDigitalSignature class"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.mock_settings = MagicMock()
        self.mock_settings.get_password = MagicMock(side_effect=lambda key: {
            "password": "test_password_123",
            "ne_key": "test_ne_key_456"
        }.get(key))
        
        self.signer = ETaxDigitalSignature(self.mock_settings)
        
        self.sample_report_data = {
            "reportNo": "RPT-2024-001",
            "taxTypeId": "VAT",
            "branchId": "001",
            "year": 2024,
            "period": 1,
            "formNo": "F001"
        }
        
        self.sample_report_detail = [
            {"tagKey": "total_sales", "tagId": "T001", "value": "1000000"},
            {"tagKey": "vat_amount", "tagId": "T002", "value": "100000"},
            {"tagKey": "net_sales", "tagId": "T003", "value": "900000"}
        ]
    
    def test_algorithm_constants(self):
        """Test algorithm constants are defined"""
        self.assertEqual(self.signer.ALGORITHM_SHA256, "SHA256")
        self.assertEqual(self.signer.ALGORITHM_SHA512, "SHA512")
        self.assertEqual(self.signer.ALGORITHM_HMAC_SHA256, "HMAC-SHA256")
    
    def test_create_signature_payload(self):
        """Test payload creation"""
        payload = self.signer.create_signature_payload(
            self.sample_report_data,
            self.sample_report_detail
        )
        
        # Should be valid JSON
        parsed = json.loads(payload)
        
        self.assertEqual(parsed["reportNo"], "RPT-2024-001")
        self.assertEqual(parsed["taxTypeId"], "VAT")
        self.assertIn("dataHash", parsed)
        self.assertIn("timestamp", parsed)
    
    def test_hash_report_detail(self):
        """Test report detail hashing"""
        hash1 = self.signer._hash_report_detail(self.sample_report_detail)
        
        # Should return a hex string
        self.assertEqual(len(hash1), 64)  # SHA256 hex length
        
        # Same data should produce same hash
        hash2 = self.signer._hash_report_detail(self.sample_report_detail)
        self.assertEqual(hash1, hash2)
        
        # Different data should produce different hash
        modified_detail = self.sample_report_detail.copy()
        modified_detail[0] = {"tagKey": "total_sales", "tagId": "T001", "value": "2000000"}
        hash3 = self.signer._hash_report_detail(modified_detail)
        self.assertNotEqual(hash1, hash3)
    
    def test_hash_report_detail_sorting(self):
        """Test that report detail is sorted for consistent hashing"""
        # Reversed order should produce same hash
        reversed_detail = list(reversed(self.sample_report_detail))
        
        hash1 = self.signer._hash_report_detail(self.sample_report_detail)
        hash2 = self.signer._hash_report_detail(reversed_detail)
        
        self.assertEqual(hash1, hash2)
    
    def test_sign_with_password(self):
        """Test password-based signing"""
        payload = "test_payload"
        result = self.signer.sign_with_password(payload, "test_password")
        
        self.assertIn("signature", result)
        self.assertIn("algorithm", result)
        self.assertIn("timestamp", result)
        self.assertEqual(result["algorithm"], "HMAC-SHA256")
        
        # Signature should be base64 encoded
        try:
            base64.b64decode(result["signature"])
        except Exception:
            self.fail("Signature is not valid base64")
    
    def test_sign_with_password_no_password(self):
        """Test signing without password raises error"""
        self.mock_settings.get_password = MagicMock(return_value=None)
        signer = ETaxDigitalSignature(self.mock_settings)
        
        with self.assertRaises(DigitalSignatureError):
            signer.sign_with_password("payload")
    
    def test_sign_with_ne_key(self):
        """Test NE-KEY signing"""
        payload = "test_payload"
        result = self.signer.sign_with_ne_key(payload)
        
        self.assertIn("signature", result)
        self.assertIn("ne_key_header", result)
        self.assertEqual(result["algorithm"], "HMAC-SHA256")
    
    def test_sign_with_ne_key_missing(self):
        """Test NE-KEY signing without key raises error"""
        self.mock_settings.get_password = MagicMock(return_value=None)
        signer = ETaxDigitalSignature(self.mock_settings)
        
        with self.assertRaises(DigitalSignatureError):
            signer.sign_with_ne_key("payload")
    
    def test_verify_signature(self):
        """Test signature verification"""
        payload = "test_payload"
        secret = "test_secret"
        
        # Create signature
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Verify
        self.assertTrue(
            self.signer.verify_signature(payload, signature_b64, secret)
        )
    
    def test_verify_signature_invalid(self):
        """Test verification of invalid signature"""
        self.assertFalse(
            self.signer.verify_signature("payload", "invalid_sig", "secret")
        )
    
    def test_verify_signature_wrong_secret(self):
        """Test verification with wrong secret"""
        payload = "test_payload"
        correct_secret = "correct_secret"
        wrong_secret = "wrong_secret"
        
        # Create signature with correct secret
        signature = hmac.new(
            correct_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Verify with wrong secret
        self.assertFalse(
            self.signer.verify_signature(payload, signature_b64, wrong_secret)
        )
    
    def test_create_submission_signature(self):
        """Test complete submission signature creation"""
        result = self.signer.create_submission_signature(
            self.sample_report_data,
            self.sample_report_detail
        )
        
        self.assertIn("payload", result)
        self.assertIn("signature", result)
        self.assertIn("algorithm", result)
        self.assertIn("timestamp", result)
        
        # Payload should be valid JSON
        json.loads(result["payload"])


class TestSignReportFunction(FrappeTestCase):
    """Tests for sign_report convenience function"""
    
    def test_sign_report(self):
        """Test sign_report function"""
        mock_settings = MagicMock()
        mock_settings.get_password = MagicMock(return_value="test_password")
        
        report_data = {
            "reportNo": "RPT-001",
            "taxTypeId": "VAT",
            "branchId": "001",
            "year": 2024,
            "period": 1,
            "formNo": "F001"
        }
        
        report_detail = [
            {"tagKey": "amount", "value": "1000"}
        ]
        
        result = sign_report(report_data, report_detail, mock_settings)
        
        self.assertIn("signature", result)
        self.assertIn("payload", result)


class TestDigitalSignatureError(FrappeTestCase):
    """Tests for DigitalSignatureError exception"""
    
    def test_exception_message(self):
        """Test exception carries message"""
        try:
            raise DigitalSignatureError("Test error message")
        except DigitalSignatureError as e:
            self.assertEqual(str(e), "Test error message")


class TestEdgeCases(FrappeTestCase):
    """Tests for edge cases and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.mock_settings = MagicMock()
        self.mock_settings.get_password = MagicMock(return_value="password")
        self.signer = ETaxDigitalSignature(self.mock_settings)
    
    def test_empty_report_detail(self):
        """Test handling of empty report detail"""
        report_data = {"reportNo": "RPT-001"}
        report_detail = []
        
        # Should not raise error
        payload = self.signer.create_signature_payload(report_data, report_detail)
        self.assertIsNotNone(payload)
    
    def test_null_values_in_detail(self):
        """Test handling of null values in report detail"""
        report_detail = [
            {"tagKey": "key1", "value": None},
            {"tagKey": "key2", "value": "valid"}
        ]
        
        # Should skip null values
        hash_result = self.signer._hash_report_detail(report_detail)
        self.assertEqual(len(hash_result), 64)
    
    def test_unicode_in_payload(self):
        """Test handling of unicode characters"""
        report_data = {
            "reportNo": "RPT-2024-монгол",
            "taxTypeId": "НӨТ"
        }
        report_detail = [
            {"tagKey": "борлуулалт", "value": "1000000₮"}
        ]
        
        payload = self.signer.create_signature_payload(report_data, report_detail)
        self.assertIsNotNone(payload)
    
    def test_large_payload(self):
        """Test handling of large payloads"""
        report_detail = [
            {"tagKey": f"key_{i}", "value": str(i * 1000)}
            for i in range(1000)
        ]
        
        hash_result = self.signer._hash_report_detail(report_detail)
        self.assertEqual(len(hash_result), 64)


class TestPayloadConsistency(FrappeTestCase):
    """Tests for payload consistency and reproducibility"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.mock_settings = MagicMock()
        self.mock_settings.get_password = MagicMock(return_value="password")
        self.signer = ETaxDigitalSignature(self.mock_settings)
    
    def test_payload_deterministic(self):
        """Test that payload generation is deterministic"""
        report_data = {
            "reportNo": "RPT-001",
            "taxTypeId": "VAT",
            "branchId": "001",
            "year": 2024,
            "period": 1,
            "formNo": "F001"
        }
        report_detail = [
            {"tagKey": "a", "value": "1"},
            {"tagKey": "b", "value": "2"}
        ]
        
        # Generate multiple times
        hashes = set()
        for _ in range(10):
            hash_result = self.signer._hash_report_detail(report_detail)
            hashes.add(hash_result)
        
        # All hashes should be identical
        self.assertEqual(len(hashes), 1)
    
    def test_signature_reproducible(self):
        """Test that same input produces same signature"""
        payload = "fixed_test_payload"
        password = "fixed_password"
        
        # Generate multiple signatures
        signatures = set()
        for _ in range(10):
            result = self.signer.sign_with_password(payload, password)
            signatures.add(result["signature"])
        
        # All signatures should be identical
        self.assertEqual(len(signatures), 1)
