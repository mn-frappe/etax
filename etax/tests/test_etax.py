# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Test Suite

Comprehensive tests for eTax app covering:
- DocTypes
- API modules (auth, client, http_client, transformer)
- Setup and configuration
- Integration tests
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


class TestETaxSettings(FrappeTestCase):
	"""Test eTax Settings DocType"""

	def test_doctype_exists(self):
		"""eTax Settings DocType should exist"""
		self.assertTrue(frappe.db.exists("DocType", "eTax Settings"))

	def test_settings_is_single(self):
		"""eTax Settings should be a single DocType"""
		doctype = frappe.get_doc("DocType", "eTax Settings")
		self.assertTrue(doctype.issingle)

	def test_settings_fields(self):
		"""eTax Settings should have required fields"""
		meta = frappe.get_meta("eTax Settings")
		field_names = [f.fieldname for f in meta.fields]

		required_fields = [
			"enabled", "environment", "username", "password",
			"ne_key", "org_regno", "api_base_url", "auth_url"
		]

		for field in required_fields:
			self.assertIn(field, field_names)

	def test_environment_options(self):
		"""Environment field should have Staging and Production options"""
		meta = frappe.get_meta("eTax Settings")
		env_field = meta.get_field("environment")

		self.assertIn("Staging", env_field.options)
		self.assertIn("Production", env_field.options)


class TestETaxReport(FrappeTestCase):
	"""Test eTax Report DocType"""

	def test_doctype_exists(self):
		"""eTax Report DocType should exist"""
		self.assertTrue(frappe.db.exists("DocType", "eTax Report"))

	def test_report_is_submittable(self):
		"""eTax Report should be submittable"""
		doctype = frappe.get_doc("DocType", "eTax Report")
		self.assertTrue(doctype.is_submittable)

	def test_report_fields(self):
		"""eTax Report should have required fields"""
		meta = frappe.get_meta("eTax Report")
		field_names = [f.fieldname for f in meta.fields]

		required_fields = [
			"report_no", "tax_report_code", "tax_type_id",
			"period_year", "period", "status", "ent_id"
		]

		for field in required_fields:
			self.assertIn(field, field_names)

	def test_status_options(self):
		"""Status field should have correct options"""
		meta = frappe.get_meta("eTax Report")
		status_field = meta.get_field("status")

		expected_statuses = ["New", "Submitted", "Assigned", "Returned", "Received"]
		for status in expected_statuses:
			self.assertIn(status, status_field.options)


class TestETaxReportDataItem(FrappeTestCase):
	"""Test eTax Report Data Item child table"""

	def test_doctype_exists(self):
		"""eTax Report Data Item DocType should exist"""
		self.assertTrue(frappe.db.exists("DocType", "eTax Report Data Item"))

	def test_is_child_table(self):
		"""Should be a child table (istable)"""
		doctype = frappe.get_doc("DocType", "eTax Report Data Item")
		self.assertTrue(doctype.istable)

	def test_fields(self):
		"""Should have tag_id, tag_key, value fields"""
		meta = frappe.get_meta("eTax Report Data Item")
		field_names = [f.fieldname for f in meta.fields]

		self.assertIn("tag_id", field_names)
		self.assertIn("tag_key", field_names)
		self.assertIn("value", field_names)


class TestETaxSubmissionLog(FrappeTestCase):
	"""Test eTax Submission Log DocType"""

	def test_doctype_exists(self):
		"""eTax Submission Log DocType should exist"""
		self.assertTrue(frappe.db.exists("DocType", "eTax Submission Log"))

	def test_log_fields(self):
		"""Submission Log should have required fields"""
		meta = frappe.get_meta("eTax Submission Log")
		field_names = [f.fieldname for f in meta.fields]

		required_fields = [
			"report", "report_no", "action", "status",
			"timestamp", "response_code", "response_message"
		]

		for field in required_fields:
			self.assertIn(field, field_names)


class TestETaxTaxpayer(FrappeTestCase):
	"""Test eTax Taxpayer DocType"""

	def test_doctype_exists(self):
		"""eTax Taxpayer DocType should exist"""
		self.assertTrue(frappe.db.exists("DocType", "eTax Taxpayer"))

	def test_taxpayer_fields(self):
		"""Taxpayer should have required fields"""
		meta = frappe.get_meta("eTax Taxpayer")
		field_names = [f.fieldname for f in meta.fields]

		required_fields = [
			"ent_id", "tin", "pin", "entity_name",
			"ent_type", "branch_code", "branch_name"
		]

		for field in required_fields:
			self.assertIn(field, field_names)


class TestETaxAuth(FrappeTestCase):
	"""Test eTax Authentication Module"""

	def test_auth_class_exists(self):
		"""ETaxAuth class should be importable"""
		from etax.api.auth import ETaxAuth
		self.assertIsNotNone(ETaxAuth)

	def test_auth_error_class(self):
		"""ETaxAuthError should be importable"""
		from etax.api.auth import ETaxAuthError
		self.assertTrue(issubclass(ETaxAuthError, Exception))

	def test_auth_urls_defined(self):
		"""Auth URLs should be defined for both environments"""
		from etax.api.auth import ETaxAuth

		self.assertIn("Staging", ETaxAuth.AUTH_URLS)
		self.assertIn("Production", ETaxAuth.AUTH_URLS)
		self.assertIn("Staging", ETaxAuth.GATEWAY_PATHS)
		self.assertIn("Production", ETaxAuth.GATEWAY_PATHS)

	def test_client_id_defined(self):
		"""Client ID should be vatps (unified ITC client)"""
		from etax.api.auth import ETaxAuth

		self.assertEqual(ETaxAuth.CLIENT_ID, "vatps")
		self.assertEqual(ETaxAuth.GRANT_TYPE, "password")


class TestETaxHTTPClient(FrappeTestCase):
	"""Test eTax HTTP Client Module"""

	def test_http_client_class_exists(self):
		"""ETaxHTTPClient class should be importable"""
		from etax.api.http_client import ETaxHTTPClient
		self.assertIsNotNone(ETaxHTTPClient)

	def test_http_error_class(self):
		"""ETaxHTTPError should be importable"""
		from etax.api.http_client import ETaxHTTPError
		self.assertTrue(issubclass(ETaxHTTPError, Exception))

	def test_http_error_attributes(self):
		"""ETaxHTTPError should have status_code and response_data"""
		from etax.api.http_client import ETaxHTTPError

		error = ETaxHTTPError("Test error", status_code=400, response_data={"error": "test"})
		self.assertEqual(error.status_code, 400)
		self.assertEqual(error.response_data, {"error": "test"})


class TestETaxClient(FrappeTestCase):
	"""Test eTax API Client Module"""

	def test_client_class_exists(self):
		"""ETaxClient class should be importable"""
		from etax.api.client import ETaxClient
		self.assertIsNotNone(ETaxClient)

	def test_endpoints_defined(self):
		"""All 14 API endpoints should be defined"""
		from etax.api.client import ETaxClient

		expected_endpoints = [
			"user_orgs", "report_list", "report_history", "late_list",
			"form_list", "form_detail", "form_data", "save_form", "submit",
			"sheet_list", "sheet_detail", "sheet_data", "save_sheet", "delete_sheet"
		]

		for endpoint in expected_endpoints:
			self.assertIn(endpoint, ETaxClient.ENDPOINTS)

	def test_client_methods_exist(self):
		"""Client should have all API methods"""
		from etax.api.client import ETaxClient

		methods = [
			"get_user_orgs", "get_report_list", "get_report_history",
			"get_late_reports", "get_form_list", "get_form_detail",
			"get_form_data", "save_form_data", "submit_report",
			"get_sheet_list", "get_sheet_detail", "get_sheet_data",
			"save_sheet_data", "delete_sheet_data"
		]

		for method in methods:
			self.assertTrue(hasattr(ETaxClient, method))


class TestETaxTransformer(FrappeTestCase):
	"""Test eTax Data Transformer Module"""

	def test_transformer_class_exists(self):
		"""ETaxTransformer class should be importable"""
		from etax.api.transformer import ETaxTransformer
		self.assertIsNotNone(ETaxTransformer)

	def test_status_map_defined(self):
		"""Status maps should be defined"""
		from etax.api.transformer import ETaxTransformer

		transformer = ETaxTransformer()

		# Check status codes
		self.assertIn(2, transformer.STATUS_MAP)
		self.assertIn(3, transformer.STATUS_MAP)
		self.assertIn(11, transformer.STATUS_MAP)

		self.assertEqual(transformer.STATUS_MAP[2], "New")
		self.assertEqual(transformer.STATUS_MAP[3], "Submitted")
		self.assertEqual(transformer.STATUS_MAP[11], "Received")

	def test_api_to_report_transformation(self):
		"""api_to_report should transform API data correctly"""
		from etax.api.transformer import ETaxTransformer

		transformer = ETaxTransformer()

		api_data = {
			"id": "12345",
			"reportNo": 9238602,
			"taxReportCode": "TT-11",
			"taxTypeId": 26,
			"taxTypeCode": "01010101",
			"taxTypeName": "Цалин хөлсний татвар",
			"periodYear": 2024,
			"period": 1,
			"taxReportStatus": 2
		}

		result = transformer.api_to_report(api_data)

		self.assertEqual(result["report_id"], "12345")
		self.assertEqual(result["report_no"], 9238602)
		self.assertEqual(result["tax_report_code"], "TT-11")
		self.assertEqual(result["status"], "New")

	def test_api_to_taxpayer_transformation(self):
		"""api_to_taxpayer should transform API data correctly"""
		from etax.api.transformer import ETaxTransformer

		transformer = ETaxTransformer()

		api_data = {
			"id": 10124763,
			"Tin": "99119911",
			"Pin": "АЧ95012118",
			"entityName": "Тестийн компани",
			"entType": 2,
			"taxpayerBranchView": {
				"branchCode": "25",
				"branchName": "Сүхбаатар дүүрэг"
			}
		}

		result = transformer.api_to_taxpayer(api_data)

		self.assertEqual(result["ent_id"], 10124763)
		self.assertEqual(result["tin"], "99119911")
		self.assertEqual(result["entity_name"], "Тестийн компани")
		self.assertEqual(result["branch_code"], "25")


class TestSetupModule(FrappeTestCase):
	"""Test Setup Module"""

	def test_install_module_exists(self):
		"""Install module should be importable"""
		from etax.setup import install
		self.assertIsNotNone(install)

	def test_after_install_function(self):
		"""after_install function should exist"""
		from etax.setup.install import after_install
		self.assertTrue(callable(after_install))

	def test_indexes_module_exists(self):
		"""Indexes module should be importable"""
		from etax.setup import indexes
		self.assertIsNotNone(indexes)


class TestHooks(FrappeTestCase):
	"""Test Hooks Configuration"""

	def test_hooks_file_exists(self):
		"""hooks.py should exist"""
		import os
		hooks_path = frappe.get_app_path("etax", "hooks.py")
		self.assertTrue(os.path.exists(hooks_path))

	def test_app_info(self):
		"""App info should be correctly defined"""
		from etax import hooks

		self.assertEqual(hooks.app_name, "etax")
		self.assertEqual(hooks.app_title, "eTax")
		self.assertIn("Digital Consulting Service", hooks.app_publisher)


class TestModuleStructure(FrappeTestCase):
	"""Test Module Structure"""

	def test_api_module_init(self):
		"""API module __init__.py should export all classes"""
		from etax.api import (
			ETaxAuth,
			ETaxClient,
			ETaxTransformer,
		)

		self.assertIsNotNone(ETaxAuth)
		self.assertIsNotNone(ETaxClient)
		self.assertIsNotNone(ETaxTransformer)

	def test_module_docstrings(self):
		"""All modules should have docstrings"""
		import etax.api.auth as auth
		import etax.api.client as client
		import etax.api.http_client as http_client
		import etax.api.transformer as transformer

		self.assertIsNotNone(auth.__doc__)
		self.assertIsNotNone(client.__doc__)
		self.assertIsNotNone(http_client.__doc__)
		self.assertIsNotNone(transformer.__doc__)


class TestPermissions(FrappeTestCase):
	"""Test DocType Permissions"""

	def test_settings_permissions(self):
		"""eTax Settings should have System Manager permission"""
		doctype = frappe.get_doc("DocType", "eTax Settings")
		roles = [p.role for p in doctype.permissions]

		self.assertIn("System Manager", roles)
		self.assertIn("Accounts Manager", roles)

	def test_report_permissions(self):
		"""eTax Report should have appropriate permissions"""
		doctype = frappe.get_doc("DocType", "eTax Report")
		roles = [p.role for p in doctype.permissions]

		self.assertIn("System Manager", roles)
		self.assertIn("Accounts Manager", roles)
		self.assertIn("Accounts User", roles)


class TestDocTypeNaming(FrappeTestCase):
	"""Test DocType Naming Rules"""

	def test_settings_naming(self):
		"""eTax Settings should be a single DocType"""
		doctype = frappe.get_doc("DocType", "eTax Settings")
		self.assertTrue(doctype.issingle)

	def test_report_naming(self):
		"""eTax Report should use autoname format"""
		doctype = frappe.get_doc("DocType", "eTax Report")
		self.assertIn("ETAX-RPT", doctype.autoname or "")

	def test_taxpayer_naming(self):
		"""eTax Taxpayer should be named by TIN field"""
		doctype = frappe.get_doc("DocType", "eTax Taxpayer")
		self.assertEqual(doctype.autoname, "field:tin")


def run_tests():
	"""Run all eTax tests"""
	# This function is called by frappe test runner
	pass


if __name__ == "__main__":
	unittest.main()
