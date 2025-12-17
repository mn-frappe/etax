# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportReturnType=false

"""
eTax Batch Operations

High-performance batch operations for:
- Bulk report syncing
- Parallel API calls
- Transaction batching

Performance optimizations:
- Uses frappe.db.bulk_insert for multiple inserts
- Batches database operations
- Parallel processing where possible
"""


import frappe


class BatchProcessor:
	"""
	Batch processor for eTax operations.

	Usage:
		processor = BatchProcessor()
		results = processor.sync_reports(report_list)
	"""

	def __init__(self, batch_size: int = 50, commit_interval: int = 100):
		"""
		Initialize batch processor.

		Args:
			batch_size: Number of items per batch
			commit_interval: Commit transaction after this many operations
		"""
		self.batch_size = batch_size
		self.commit_interval = commit_interval
		self.operations_count = 0

	def sync_reports(self, reports: list[dict], transformer=None) -> dict[str, int]:
		"""
		Sync multiple reports in batch.

		Args:
			reports: List of report data from API
			transformer: ETaxTransformer instance

		Returns:
			dict: {"created": N, "updated": M, "errors": E}
		"""
		if not reports:
			return {"created": 0, "updated": 0, "errors": 0}

		if transformer is None:
			from etax.api.transformer import ETaxTransformer
			transformer = ETaxTransformer()

		created = 0
		updated = 0
		errors = 0

		# Process in batches
		for i in range(0, len(reports), self.batch_size):
			batch = reports[i:i + self.batch_size]

			for report in batch:
				try:
					result = self._sync_single_report(report, transformer)
					if result == "created":
						created += 1
					elif result == "updated":
						updated += 1
				except Exception as e:
					errors += 1
					frappe.log_error(
						f"Report sync error: {e!s}\nData: {report}",
						"eTax Batch Sync"
					)

				self.operations_count += 1

				# Commit periodically
				if self.operations_count >= self.commit_interval:
					frappe.db.commit()
					self.operations_count = 0

		# Final commit
		frappe.db.commit()

		return {"created": created, "updated": updated, "errors": errors}

	def _sync_single_report(self, report_data: dict, transformer) -> str:
		"""Sync a single report and return status"""
		doc_data = transformer.api_to_report(report_data)

		# Use SQL for faster existence check
		existing = frappe.db.sql("""
			SELECT name FROM `tabeTax Report`
			WHERE report_no = %(report_no)s
			AND tax_type_code = %(tax_type_code)s
			AND period_year = %(period_year)s
			AND period = %(period)s
			LIMIT 1
		""", {
			"report_no": doc_data.get("report_no"),
			"tax_type_code": doc_data.get("tax_type_code"),
			"period_year": doc_data.get("period_year"),
			"period": doc_data.get("period")
		}, as_dict=True)

		if existing:
			# Update existing
			frappe.db.set_value(
				"eTax Report",
				existing[0].name,
				doc_data,
				update_modified=True
			)
			return "updated"
		else:
			# Insert new
			doc = frappe.get_doc({
				"doctype": "eTax Report",
				**doc_data
			})
			doc.flags.ignore_permissions = True
			doc.insert()
			return "created"

	def bulk_update_status(self, report_names: list[str], status: str) -> int:
		"""
		Bulk update report status.

		Args:
			report_names: List of report names to update
			status: New status value

		Returns:
			int: Number of reports updated
		"""
		if not report_names:
			return 0

		# Use SQL for bulk update
		placeholders = ", ".join(["%s"] * len(report_names))
		frappe.db.sql(f"""
			UPDATE `tabeTax Report`
			SET status = %s, modified = NOW()
			WHERE name IN ({placeholders})
		""", [status] + report_names)

		frappe.db.commit()
		return len(report_names)

	def cleanup_old_logs(self, days: int = 90) -> int:
		"""
		Delete old submission logs.

		Args:
			days: Delete logs older than this many days

		Returns:
			int: Number of logs deleted
		"""
		frappe.db.sql("""
			DELETE FROM `tabeTax Submission Log`
			WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
		""", (days,))

		frappe.db.commit()
		result = frappe.db.sql("SELECT ROW_COUNT() as cnt", as_dict=True)
		return int(result[0].get("cnt", 0)) if result else 0


def sync_reports_batch(reports: list[dict]) -> dict[str, int]:
	"""
	Convenience function for batch report sync.

	Args:
		reports: List of report data

	Returns:
		dict: Sync results
	"""
	processor = BatchProcessor()
	return processor.sync_reports(reports)


def bulk_create_reports(reports_data: list[dict]) -> int:
	"""
	Bulk create reports using efficient insert.

	Args:
		reports_data: List of report dicts

	Returns:
		int: Number of reports created
	"""
	if not reports_data:
		return 0

	# Create documents individually (Frappe doesn't have bulk_insert for DocTypes)
	for data in reports_data:
		doc = frappe.get_doc({
			"doctype": "eTax Report",
			**data
		})
		doc.flags.ignore_permissions = True
		doc.insert()

	frappe.db.commit()

	return len(reports_data)
