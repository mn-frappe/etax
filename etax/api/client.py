# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eTax API Client

Full implementation of eTax API (14 endpoints) with performance optimizations:
- Connection pooling (reuse TCP connections)
- Response caching (Redis)
- Lazy loading
- Bulk operations support

User/Org Management:
1. getUserOrgs - Get user's organizations

Tax Report Management:
2. getList - Get pending tax reports list
3. getHistory - Get report history by year
4. getLateList - Get overdue reports list
5. getFormList - Get form templates for tax type
6. getFormDetail - Get form structure/schema
7. getFormData - Get report data
8. saveFormData - Save report (draft)
9. submit - Submit report (final)

Sheet/Attachment Management:
10. getSheetList - Get attachment sheets list
11. getSheetDetail - Get sheet structure
12. getSheetData - Get sheet data
13. saveSheetData - Save sheet data
14. deleteAllSheetData - Delete all sheet data
"""

import frappe

from etax.api.auth import ETaxAuth
from etax.api.cache import (
	get_cached_form_detail,
	get_cached_orgs,
	set_cached_form_detail,
	set_cached_orgs,
)
from etax.api.http_client import ETaxHTTPClient


class ETaxClient:
	"""
	eTax API Client for Mongolia Tax Authority Electronic Tax System.

	Usage:
		client = ETaxClient()

		# Get organizations
		orgs = client.get_user_orgs()

		# Get pending reports
		reports = client.get_report_list(ent_id)

		# Submit report
		result = client.submit_report(report_data)
	"""

	# API endpoint paths (relative to base URL)
	ENDPOINTS = {
		# User/Org
		"user_orgs": "/user/getUserOrgs",

		# Tax Reports
		"report_list": "/return/getList",
		"report_history": "/return/getHistory",
		"late_list": "/return/getLateList",
		"form_list": "/return/getFormList",
		"form_detail": "/return/getFormDetail",
		"form_data": "/return/getFormData",
		"save_form": "/return/saveFormData",
		"submit": "/return/submit",

		# Sheets/Attachments
		"sheet_list": "/return/getSheetList",
		"sheet_detail": "/return/getSheetDetail",
		"sheet_data": "/return/getSheetData",
		"save_sheet": "/return/saveSheetData",
		"delete_sheet": "/return/deleteAllSheetData"
	}

	def __init__(self, settings=None):
		"""
		Initialize eTax client.

		Args:
			settings: eTax Settings doc or None
		"""
		self.settings = settings or self._get_settings()
		self.auth = ETaxAuth(self.settings)
		self.http = ETaxHTTPClient(self.settings)

	def _get_settings(self):
		"""Get eTax Settings singleton"""
		return frappe.get_single("eTax Settings")

	def _get_auth_header(self):
		"""Get authorization header"""
		return self.auth.get_auth_header()

	def _get_ent_id(self, ent_id=None):
		"""Get entity ID from settings or parameter"""
		if ent_id:
			return ent_id
		# Would be stored after get_user_orgs call
		return getattr(self.settings, 'ent_id', None)

	# =========================================================================
	# API 1: Get User Organizations
	# =========================================================================

	def get_user_orgs(self, skip_cache=False):
		"""
		Get user's registered organizations (татвар төлөгчийн мэдээлэл).

		Cached for 1 hour (organizations rarely change).

		Args:
			skip_cache: Skip cache and fetch fresh data

		Returns:
			list: List of organizations with:
				- id: Entity ID (ent_id for other API calls)
				- Tin: Taxpayer Identification Number
				- Pin: Registry Number
				- entityName: Organization name
				- entType: 1=Individual, 2=Legal Entity
				- taxpayerBranchView: Tax office info

		Example response:
			{
				"id": 10124763,
				"Tin": "99119911",
				"Pin": "99119911",
				"entityName": "ТЕСТИЙН ХЭРЭГЛЭГЧ 1",
				"entType": 2,
				"taxpayerBranchView": {
					"branchCode": "25",
					"branchName": "Сүхбаатар дүүрэг"
				}
			}
		"""
		# Check cache first
		cache_key = self.settings.org_regno or "default"
		if not skip_cache:
			cached_orgs = get_cached_orgs(cache_key)
			if cached_orgs:
				return cached_orgs

		# Note: getUserOrgs uses different base path (no /beta)
		response = self.http.get(
			"/user/getUserOrgs",
			auth_header=self._get_auth_header()
		)

		# Cache result
		if response:
			orgs_list = response if isinstance(response, list) else [response]
			set_cached_orgs(cache_key, orgs_list)

		return response

	# =========================================================================
	# API 2: Get Report List (Pending Reports)
	# =========================================================================

	def get_report_list(self, ent_id=None):
		"""
		Get list of pending tax reports (тушаах тайлангийн жагсаалт).

		Args:
			ent_id: Entity/taxpayer ID

		Returns:
			list: List of reports with:
				- id: Report ID
				- taxReportCode: Report code (e.g., "TT-11")
				- taxTypeName: Tax type name
				- periodYear: Reporting year
				- period: Reporting period (quarter)
				- returnDueDate: Due date
				- taxReportStatus: Status code
				- taxReportStatusName: Status name

		Status codes:
			2 - New (Шинэ)
			3 - Submitted (Илгээсэн)
			6 - Assigned (Хариуцуулсан)
			8 - Returned (Буцаасан)
			11 - Received (Хүлээн авсан)
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["report_list"],
			auth_header=self._get_auth_header(),
			params={"entId": ent_id}
		)

		return response.get("reportList", [])

	# =========================================================================
	# API 3: Get Report History
	# =========================================================================

	def get_report_history(self, year, ent_id=None):
		"""
		Get report history for a specific year (тайлангийн түүх).

		Args:
			year: Reporting year (e.g., 2024)
			ent_id: Entity/taxpayer ID

		Returns:
			list: Historical reports grouped by tax type
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["report_history"],
			auth_header=self._get_auth_header(),
			params={"year": year, "entId": ent_id}
		)

		return response.get("historyList", [])

	# =========================================================================
	# API 4: Get Late/Overdue Reports
	# =========================================================================

	def get_late_reports(self, ent_id=None):
		"""
		Get list of overdue/late reports (хоцорсон тайлангийн жагсаалт).

		Args:
			ent_id: Entity/taxpayer ID

		Returns:
			list: List of overdue reports
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["late_list"],
			auth_header=self._get_auth_header(),
			params={"entId": ent_id}
		)

		return response.get("reportLateList", [])

	# =========================================================================
	# API 5: Get Form List
	# =========================================================================

	def get_form_list(self, form_no, ent_id=None):
		"""
		Get form templates for a tax report type (маягтын жагсаалт).

		Args:
			form_no: Form number (e.g., 1108 for TT-11)
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Form list with subforms and expression cells
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["form_list"],
			auth_header=self._get_auth_header(),
			params={"formNo": form_no, "entId": ent_id}
		)

		return response.get("reportFormList", {})

	# =========================================================================
	# API 6: Get Form Detail/Structure
	# =========================================================================

	def get_form_detail(self, form_no, tax_type_id, branch_id, year, period, ent_id=None, skip_cache=False):
		"""
		Get form structure/schema (маягтын загвар).

		This returns the complete form structure needed to render
		and fill the tax report form dynamically.

		Cached for 24 hours (form structures rarely change).

		Args:
			form_no: Form number
			tax_type_id: Tax type ID
			branch_id: Tax office branch ID
			year: Reporting year
			period: Reporting period
			ent_id: Entity/taxpayer ID
			skip_cache: Skip cache and fetch fresh

		Returns:
			dict: Form structure with:
				- reportFormInfo: Form metadata
				- headers: Table headers
				- sections: Form sections with cells
				- validations: Validation rules
		"""
		# Check cache first (form structures are static)
		cache_key = f"{form_no}:{tax_type_id}:{year}"
		if not skip_cache:
			cached_detail = get_cached_form_detail(cache_key)
			if cached_detail:
				return cached_detail

		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["form_detail"],
			auth_header=self._get_auth_header(),
			params={
				"formNo": form_no,
				"taxTypeId": tax_type_id,
				"branchId": branch_id,
				"year": year,
				"period": period,
				"entId": ent_id
			}
		)

		result = response.get("reportFormPass", {})

		# Cache result
		if result:
			set_cached_form_detail(cache_key, result)

		return result

	# =========================================================================
	# API 7: Get Form Data
	# =========================================================================

	def get_form_data(self, report_id, ent_id=None):
		"""
		Get report data for a specific report (тайлангийн мэдээлэл).

		Args:
			report_id: Report ID (reportNo)
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Report data with:
				- reportData: Report metadata
				- reportDataDetail: Cell values (tagId, tagKey, value)
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["form_data"],
			auth_header=self._get_auth_header(),
			params={"reportId": report_id, "entId": ent_id}
		)

		return response.get("reportDataGet", {})

	# =========================================================================
	# API 8: Save Form Data (Draft)
	# =========================================================================

	def save_form_data(self, report_data, report_data_detail, ent_id=None):
		"""
		Save report data as draft (тайлан хадгалах).

		Args:
			report_data: Report metadata dict with:
				- reportNo: Report ID
				- taxTypeId: Tax type ID
				- branchId: Tax office ID
				- year: Reporting year
				- period: Reporting period
				- isXreport: 0=normal, 1=X-report (no activity)
				- formNo: Form number
			report_data_detail: List of cell values with:
				- tagId: Cell ID
				- tagKey: Cell key (e.g., "TAG001A")
				- value: Cell value
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Save result with code and message
		"""
		ent_id = self._get_ent_id(ent_id)

		payload = {
			"reportData": report_data,
			"reportDataDetail": report_data_detail
		}

		response = self.http.post(
			self.ENDPOINTS["save_form"],
			data=payload,
			auth_header=self._get_auth_header(),
			params={"entId": ent_id}
		)

		return response

	# =========================================================================
	# API 9: Submit Report (Final)
	# =========================================================================

	def submit_report(self, report_data, ent_id=None):
		"""
		Submit report to tax authority (тайлан илгээх).

		IMPORTANT: Report must be saved first using save_form_data().
		Submission validates against form validations.

		Args:
			report_data: Report metadata dict with:
				- reportNo: Report ID
				- taxTypeId: Tax type ID
				- branchId: Tax office ID
				- year: Reporting year
				- period: Reporting period
				- isXreport: X-report flag
				- formNo: Form number
				- reportStatusId: Should be 3 for submit
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Submit result with code and message
		"""
		ent_id = self._get_ent_id(ent_id)

		# Ensure status is set for submission
		if "reportStatusId" not in report_data:
			report_data["reportStatusId"] = 3

		response = self.http.post(
			self.ENDPOINTS["submit"],
			data=report_data,
			auth_header=self._get_auth_header(),
			params={"entId": ent_id}
		)

		return response

	# =========================================================================
	# API 10: Get Sheet List (Attachments)
	# =========================================================================

	def get_sheet_list(self, form_no, report_no=None, ent_id=None):
		"""
		Get attachment sheets for a form (хавсралт мэдээний жагсаалт).

		Args:
			form_no: Form number
			report_no: Report ID (optional if not saved yet)
			ent_id: Entity/taxpayer ID

		Returns:
			list: Sheet forms with metadata and status
		"""
		ent_id = self._get_ent_id(ent_id)

		params = {"formNo": form_no, "entId": ent_id}
		if report_no:
			params["reportNo"] = report_no

		response = self.http.get(
			self.ENDPOINTS["sheet_list"],
			auth_header=self._get_auth_header(),
			params=params
		)

		return response.get("sheetFormList", [])

	# =========================================================================
	# API 11: Get Sheet Detail/Structure
	# =========================================================================

	def get_sheet_detail(self, sheet_form_no, ent_id=None):
		"""
		Get sheet structure/schema (мэдээний загвар).

		Args:
			sheet_form_no: Sheet form number
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Sheet structure with:
				- sheetInfo: Sheet metadata
				- headers: Column headers
				- rowModel: Row template with column definitions
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["sheet_detail"],
			auth_header=self._get_auth_header(),
			params={"sheetFormNo": sheet_form_no, "entId": ent_id}
		)

		return response.get("sheetFormDetail", {})

	# =========================================================================
	# API 12: Get Sheet Data
	# =========================================================================

	def get_sheet_data(self, sheet_form_no, report_no, page=1, size=100, ent_id=None):
		"""
		Get sheet data (мэдээний өгөгдөл).

		Args:
			sheet_form_no: Sheet form number
			report_no: Report ID
			page: Page number (for pagination)
			size: Page size
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Sheet data with rows and cells
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["sheet_data"],
			auth_header=self._get_auth_header(),
			params={
				"sheetFormNo": sheet_form_no,
				"reportNo": report_no,
				"page": page,
				"size": size,
				"entId": ent_id
			}
		)

		return response.get("sheetData", {})

	# =========================================================================
	# API 13: Save Sheet Data
	# =========================================================================

	def save_sheet_data(self, sheet_form_no, sheet_code, report_no, sheet_data_detail, ent_id=None):
		"""
		Save sheet data (мэдээ хадгалах).

		Args:
			sheet_form_no: Sheet form number
			sheet_code: Sheet code (e.g., "XM_11(1)")
			report_no: Report ID
			sheet_data_detail: List of row data with cells
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Save result
		"""
		ent_id = self._get_ent_id(ent_id)

		payload = {
			"sheetFormNo": sheet_form_no,
			"sheetCode": sheet_code,
			"reportNo": report_no,
			"sheetDataDetail": sheet_data_detail
		}

		response = self.http.post(
			self.ENDPOINTS["save_sheet"],
			data=payload,
			auth_header=self._get_auth_header(),
			params={"entId": ent_id}
		)

		return response

	# =========================================================================
	# API 14: Delete All Sheet Data
	# =========================================================================

	def delete_sheet_data(self, sheet_form_no, report_no, ent_id=None):
		"""
		Delete all data from a sheet (мэдээг устгах).

		Args:
			sheet_form_no: Sheet form number
			report_no: Report ID
			ent_id: Entity/taxpayer ID

		Returns:
			dict: Delete result
		"""
		ent_id = self._get_ent_id(ent_id)

		response = self.http.get(
			self.ENDPOINTS["delete_sheet"],
			auth_header=self._get_auth_header(),
			params={
				"sheetFormNo": sheet_form_no,
				"reportNo": report_no,
				"entId": ent_id
			}
		)

		return response


def get_client():
	"""Get eTax Client instance"""
	return ETaxClient()
