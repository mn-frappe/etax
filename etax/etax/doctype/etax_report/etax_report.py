# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
eTax Report DocType

Represents a tax report to be submitted to Mongolia Tax Authority (MTA).
"""

import frappe
from frappe import _
from frappe.model.document import Document


class eTaxReport(Document):
	"""
	eTax Report - Tax report for MTA submission.

	Workflow:
	1. Sync from API (get_report_list) or create manually
	2. Fill data (data_items)
	3. Save draft (saves to MTA)
	4. Submit (sends to MTA)
	"""

	def validate(self):
		"""Validate report before save"""
		self.validate_period()
		self.validate_tax_type()

	def validate_period(self):
		"""Validate reporting period"""
		if self.period_year and self.period_year < 2000:
			frappe.throw(_("Invalid reporting year"))

		if self.period and (self.period < 1 or self.period > 4):
			frappe.throw(_("Period must be between 1 and 4 (quarters)"))

	def validate_tax_type(self):
		"""Validate tax type information"""
		if not self.tax_type_id and not self.tax_type_code:
			frappe.throw(_("Tax type is required"))

	def before_submit(self):
		"""Before submitting report"""
		self.submit_to_mta()

	def on_cancel(self):
		"""Handle report cancellation"""
		frappe.msgprint(_("Note: Cancellation in ERPNext does not cancel the report in MTA"))

	@frappe.whitelist()
	def save_to_mta(self):
		"""
		Save report draft to MTA.

		Returns:
			dict: Save result
		"""
		try:
			from etax.api.client import ETaxClient
			from etax.api.transformer import ETaxTransformer

			client = ETaxClient()
			transformer = ETaxTransformer()

			# Transform data
			report_data, report_data_detail = transformer.form_data_to_api(
				self,
				self.data_items
			)

			# Save to MTA
			result = client.save_form_data(report_data, report_data_detail, self.ent_id)

			# Log
			self._create_submission_log("Save", result)

			frappe.msgprint(_("Report saved to MTA successfully"))
			return {"success": True, "result": result}

		except Exception as e:
			frappe.log_error(f"eTax save failed: {e!s}", "eTax Report")
			frappe.throw(_("Failed to save report to MTA: {0}").format(str(e)))

	def submit_to_mta(self):
		"""
		Submit report to MTA (final submission).

		Called automatically before_submit.
		"""
		settings = frappe.get_single("eTax Settings")
		if not settings.enabled:
			frappe.msgprint(_("eTax integration is disabled. Report not sent to MTA."))
			return

		try:
			from etax.api.client import ETaxClient
			from etax.api.transformer import ETaxTransformer

			client = ETaxClient()
			transformer = ETaxTransformer()

			# Transform data
			report_data = transformer.report_to_api(self)

			# Submit to MTA
			result = client.submit_report(report_data, self.ent_id)

			# Update status
			self.status = "Submitted"
			self.submitted_date = frappe.utils.now()

			# Log
			self._create_submission_log("Submit", result)

			frappe.msgprint(_("Report submitted to MTA successfully"))

		except Exception as e:
			frappe.log_error(f"eTax submit failed: {e!s}", "eTax Report")
			frappe.throw(_("Failed to submit report to MTA: {0}").format(str(e)))

	@frappe.whitelist()
	def refresh_from_mta(self):
		"""
		Refresh report data from MTA.

		Returns:
			dict: Updated data
		"""
		try:
			from etax.api.client import ETaxClient
			from etax.api.transformer import ETaxTransformer

			client = ETaxClient()
			transformer = ETaxTransformer()

			# Get form data
			api_data = client.get_form_data(self.report_no, self.ent_id)

			# Transform and update
			result = transformer.api_to_form_data(api_data)
			form_data = result["form_data"]

			# Update fields
			for key, value in form_data.items():
				if hasattr(self, key) and value is not None:
					setattr(self, key, value)

			# Update data items
			self.data_items = []
			for item in result["detail_items"]:
				self.append("data_items", item)

			self.save()

			frappe.msgprint(_("Report refreshed from MTA"))
			return {"success": True}

		except Exception as e:
			frappe.log_error(f"eTax refresh failed: {e!s}", "eTax Report")
			return {"success": False, "message": str(e)}

	def _create_submission_log(self, action, result):
		"""Create submission log entry"""
		try:
			log = frappe.get_doc({
				"doctype": "eTax Submission Log",
				"report": self.name,
				"report_no": self.report_no,
				"action": action,
				"status": "Success" if result.get("code", 0) == 0 else "Failed",
				"response_code": result.get("code"),
				"response_message": result.get("message"),
				"timestamp": frappe.utils.now()
			})
			log.insert(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to create submission log: {e!s}", "eTax")


@frappe.whitelist()
def sync_reports(ent_id=None):
	"""
	Sync pending reports from MTA.

	Args:
		ent_id: Entity ID (optional, uses settings default)

	Returns:
		dict: Sync result
	"""
	from etax.api.client import ETaxClient
	from etax.api.transformer import ETaxTransformer

	client = ETaxClient()
	transformer = ETaxTransformer()

	reports = client.get_report_list(ent_id)

	synced = 0
	for report_data in reports:
		doc_data = transformer.api_to_report(report_data)

		# Check if exists
		existing = frappe.db.exists("eTax Report", {
			"report_no": doc_data.get("report_no"),
			"tax_type_code": doc_data.get("tax_type_code"),
			"period_year": doc_data.get("period_year"),
			"period": doc_data.get("period")
		})

		if existing:
			doc = frappe.get_doc("eTax Report", existing)
			doc.update(doc_data)
			doc.save()
		else:
			doc = frappe.get_doc({
				"doctype": "eTax Report",
				**doc_data
			})
			doc.insert()

		synced += 1

	frappe.db.commit()

	return {"success": True, "synced": synced}
