# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false

"""
eTax API - Data Transformer Module

Transforms data between eTax API format and Frappe DocType format.
"""

import frappe
from datetime import datetime


class ETaxTransformer:
	"""
	Transform eTax API data to/from Frappe DocTypes.
	
	API -> DocType: api_to_*
	DocType -> API: *_to_api
	"""
	
	# =========================================================================
	# Report Status Mapping
	# =========================================================================
	
	# eTax status codes to names
	STATUS_MAP = {
		2: "New",           # Шинэ
		3: "Submitted",     # Илгээсэн
		6: "Assigned",      # Хариуцуулсан
		8: "Returned",      # Буцаасан
		11: "Received"      # Хүлээн авсан
	}
	
	STATUS_MAP_MN = {
		2: "Шинэ",
		3: "Илгээсэн",
		6: "Хариуцуулсан",
		8: "Буцаасан",
		11: "Хүлээн авсан"
	}
	
	# =========================================================================
	# Report List Transformation
	# =========================================================================
	
	def api_to_report(self, api_data):
		"""
		Transform API report data to eTax Report DocType format.
		
		Args:
			api_data: Report data from API (getList, getHistory)
			
		Returns:
			dict: Data for eTax Report DocType
		"""
		return {
			"report_id": api_data.get("id"),
			"report_no": api_data.get("reportNo"),
			"tax_report_code": api_data.get("taxReportCode"),
			"tax_type_id": api_data.get("taxTypeId"),
			"tax_type_code": api_data.get("taxTypeCode"),
			"tax_type_name": api_data.get("taxTypeName"),
			"form_no": api_data.get("formNo"),
			"branch_id": api_data.get("branchId"),
			"branch_code": api_data.get("branchCode"),
			"branch_name": api_data.get("branchName"),
			"period_id": api_data.get("periodId"),
			"period_year": api_data.get("periodYear"),
			"period": api_data.get("period"),
			"period_name": api_data.get("periodName"),
			"return_begin_date": self._parse_date(api_data.get("returnBeginDate")),
			"return_due_date": self._parse_date(api_data.get("returnDueDate")),
			"status": self.STATUS_MAP.get(api_data.get("taxReportStatus"), "Unknown"),
			"status_code": api_data.get("taxReportStatus"),
			"status_name": api_data.get("taxReportStatusName"),
			"license_no": api_data.get("licenseNo"),
			"revenue_id": api_data.get("revenueId"),
			"sub_branch_id": api_data.get("subBranchId"),
			"sub_branch_code": api_data.get("subBranchCode"),
			"sub_branch_name": api_data.get("subBranchName")
		}
	
	def report_to_api(self, doc):
		"""
		Transform eTax Report DocType to API format for save/submit.
		
		Args:
			doc: eTax Report document
			
		Returns:
			dict: Data for API request
		"""
		return {
			"reportNo": doc.report_no,
			"taxTypeId": doc.tax_type_id,
			"branchId": doc.branch_id,
			"year": doc.period_year,
			"period": doc.period,
			"isXreport": 1 if doc.is_x_report else 0,
			"formNo": doc.form_no,
			"activitiType": doc.activity_type or 1,
			"resubmitId": doc.resubmit_id or 0,
			"fileGroupId": doc.file_group_id or "",
			"reportStatusId": self._get_status_code(doc.status)
		}
	
	# =========================================================================
	# Form Data Transformation
	# =========================================================================
	
	def api_to_form_data(self, api_data):
		"""
		Transform API form data to DocType format.
		
		Args:
			api_data: Response from getFormData
			
		Returns:
			dict: Form data and detail items
		"""
		report_data = api_data.get("reportData", {})
		detail = api_data.get("reportDataDetail", [])
		
		form_data = {
			"report_no": report_data.get("reportNo"),
			"report_uuid": report_data.get("reportNoStr"),
			"tax_type_id": report_data.get("taxTypeId"),
			"tax_type_code": report_data.get("taxTypeCode"),
			"tax_type_desc": report_data.get("taxTypeDesc"),
			"branch_id": report_data.get("branchId"),
			"branch_code": report_data.get("branchCode"),
			"branch_name": report_data.get("branchName"),
			"form_no": report_data.get("formNo"),
			"ent_id": report_data.get("entId"),
			"ent_name": report_data.get("entName"),
			"pin": report_data.get("pin"),
			"period_year": report_data.get("year"),
			"period": report_data.get("period"),
			"is_x_report": report_data.get("isXreport") == 1,
			"status_code": report_data.get("reportStatusId"),
			"status_name": report_data.get("reportStatusName"),
			"received_date": self._parse_datetime(report_data.get("recievedDate")),
			"received_emp": report_data.get("recievedEmp"),
			"submitted_date": self._parse_datetime(report_data.get("submittedDate")),
			"done_date": self._parse_datetime(report_data.get("doneDate"))
		}
		
		# Transform detail items
		detail_items = []
		for item in detail:
			detail_items.append({
				"tag_id": item.get("tagId"),
				"tag_key": item.get("tagKey"),
				"value": item.get("value"),
				"type": item.get("type")
			})
		
		return {"form_data": form_data, "detail_items": detail_items}
	
	def form_data_to_api(self, doc, detail_items):
		"""
		Transform form data DocType to API format.
		
		Args:
			doc: eTax Report document
			detail_items: List of data items
			
		Returns:
			tuple: (report_data, report_data_detail)
		"""
		report_data = {
			"reportNo": doc.report_no,
			"taxTypeId": str(doc.tax_type_id),
			"branchId": str(doc.branch_id),
			"year": doc.period_year,
			"period": doc.period,
			"isXreport": 1 if doc.is_x_report else 0,
			"formNo": doc.form_no,
			"activitiType": 1,
			"resubmitId": 0,
			"fileGroupId": "",
			"reportStatusId": None
		}
		
		report_data_detail = []
		for item in detail_items:
			report_data_detail.append({
				"tagId": item.tag_id,
				"tagKey": item.tag_key,
				"value": str(item.value) if item.value else "",
				"toolTipOpen": False,
				"errorMsgs": "",
				"errType": "",
				"type": item.type or 1,
				"isValid": True
			})
		
		return report_data, report_data_detail
	
	# =========================================================================
	# Form Structure Transformation
	# =========================================================================
	
	def api_to_form_structure(self, api_data):
		"""
		Transform API form structure to DocType format.
		
		Args:
			api_data: Response from getFormDetail
			
		Returns:
			dict: Form structure data
		"""
		form_info = api_data.get("reportFormInfo", {})
		sections = api_data.get("sections", [])
		
		structure = {
			"report_code": form_info.get("reportCode"),
			"form_no": form_info.get("formNo"),
			"tax_type_code": form_info.get("taxTypeCode"),
			"report_name": form_info.get("reportName"),
			"report_frequency": form_info.get("reportFrequency"),
			"report_statement": form_info.get("reportStatement"),
			"version": form_info.get("version"),
			"sections": []
		}
		
		# Transform sections
		for section in sections:
			section_data = {
				"title": section.get("title"),
				"key": section.get("key"),
				"section_no": section.get("sectionNo"),
				"sequence": section.get("sequence"),
				"type": section.get("type"),
				"header_html": section.get("headerHtml"),
				"headers": section.get("headers", []),
				"rows": []
			}
			
			# Transform rows
			for row in section.get("rows", []):
				row_data = {
					"row_number": row.get("rowNumber"),
					"hidden": row.get("hidden", False),
					"cells": []
				}
				
				# Transform cells
				for cell in row.get("cells", []):
					cell_data = {
						"name": cell.get("name"),
						"column_key": cell.get("columnKey"),
						"column_sequence": cell.get("columnSequence"),
						"tag_id": cell.get("tagId"),
						"default_value": cell.get("defaultValue"),
						"regex": cell.get("regex"),
						"expression": cell.get("expression"),
						"data_type": cell.get("dataType"),
						"draw_type": cell.get("drawType"),
						"is_tag": cell.get("isTag"),
						"is_disable": cell.get("isDisable"),
						"allow_minus": cell.get("allowMinus"),
						"row_span": cell.get("rowSpan"),
						"is_assessment": cell.get("isAssessment"),
						"validations": cell.get("validations", [])
					}
					row_data["cells"].append(cell_data)
				
				section_data["rows"].append(row_data)
			
			structure["sections"].append(section_data)
		
		return structure
	
	# =========================================================================
	# Sheet Data Transformation
	# =========================================================================
	
	def api_to_sheet_data(self, api_data):
		"""
		Transform API sheet data to DocType format.
		
		Args:
			api_data: Response from getSheetData
			
		Returns:
			dict: Sheet data
		"""
		return {
			"sheet_form_no": api_data.get("sheetFormNo"),
			"sheet_code": api_data.get("sheetCode"),
			"report_no": api_data.get("reportNo"),
			"map_id": api_data.get("mapId"),
			"rows": [
				{
					"row_number": item.get("rowNumber"),
					"is_total": item.get("isTotal") == 1,
					"type": item.get("type"),
					"cells": item.get("cells", [])
				}
				for item in api_data.get("sheetDataDetail", [])
			]
		}
	
	def sheet_data_to_api(self, sheet_form_no, sheet_code, report_no, rows):
		"""
		Transform sheet data to API format for save.
		
		Args:
			sheet_form_no: Sheet form number
			sheet_code: Sheet code
			report_no: Report ID
			rows: List of row data
			
		Returns:
			dict: API request payload
		"""
		sheet_data_detail = []
		
		for row in rows:
			cells = []
			for cell in row.get("cells", []):
				cells.append({
					"key": cell.get("key"),
					"value": str(cell.get("value", "")),
					"isValid": True,
					"toolTipOpen": False,
					"errType": "",
					"errMsg": ""
				})
			
			sheet_data_detail.append({
				"rowNumber": row.get("row_number"),
				"isTotal": 1 if row.get("is_total") else 0,
				"isChecked": True,
				"isEdit": False,
				"type": row.get("type"),
				"cells": cells
			})
		
		return {
			"sheetFormNo": sheet_form_no,
			"sheetCode": sheet_code,
			"reportNo": report_no,
			"sheetDataDetail": sheet_data_detail
		}
	
	# =========================================================================
	# Taxpayer/Organization Transformation
	# =========================================================================
	
	def api_to_taxpayer(self, api_data):
		"""
		Transform API organization data to eTax Taxpayer DocType.
		
		Args:
			api_data: Response from getUserOrgs
			
		Returns:
			dict: Data for eTax Taxpayer DocType
		"""
		branch_view = api_data.get("taxpayerBranchView", {})
		ref_ent_type = api_data.get("refEntType", {})
		ref_status = api_data.get("refEntStatus", {})
		
		return {
			"ent_id": api_data.get("id"),
			"tin": api_data.get("Tin"),
			"pin": api_data.get("Pin"),
			"entity_name": api_data.get("entityName"),
			"ent_type": api_data.get("entType"),
			"ent_type_name": ref_ent_type.get("name"),
			"ent_status": api_data.get("entStatus"),
			"ent_status_name": ref_status.get("name"),
			"parent_id": api_data.get("parentId"),
			"is_confirmed": api_data.get("isConfirmed") == 1,
			"branch_code": branch_view.get("branchCode"),
			"branch_name": branch_view.get("branchName"),
			"sub_branch_code": branch_view.get("subBranchCode"),
			"sub_branch_name": branch_view.get("subBranchName"),
			"agree_general_role_user": api_data.get("agreeGeneralRoleUser"),
			"ebarimt_login": api_data.get("ebarimtLogin")
		}
	
	# =========================================================================
	# Helper Methods
	# =========================================================================
	
	def _parse_date(self, date_str):
		"""Parse date string to date object"""
		if not date_str:
			return None
		
		try:
			if isinstance(date_str, datetime):
				return date_str.date()
			
			# Try common formats
			for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
				try:
					return datetime.strptime(date_str, fmt).date()
				except ValueError:
					continue
			
			return None
		except Exception:
			return None
	
	def _parse_datetime(self, dt_str):
		"""Parse datetime string to datetime object"""
		if not dt_str:
			return None
		
		try:
			if isinstance(dt_str, datetime):
				return dt_str
			
			# Try common formats
			for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
				try:
					return datetime.strptime(dt_str, fmt)
				except ValueError:
					continue
			
			return None
		except Exception:
			return None
	
	def _get_status_code(self, status_name):
		"""Get status code from status name"""
		reverse_map = {v: k for k, v in self.STATUS_MAP.items()}
		return reverse_map.get(status_name, 2)  # Default to "New"


def get_transformer():
	"""Get ETaxTransformer instance"""
	return ETaxTransformer()
