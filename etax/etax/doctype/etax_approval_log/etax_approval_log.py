# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Approval Log

Tracks all approval workflow actions for tax report submissions.
Provides audit trail for compliance and accountability.
"""

import frappe
from frappe import utils
from frappe.model.document import Document


class eTaxApprovalLog(Document):
	"""eTax Approval Log - Audit trail for tax report approvals"""

	def before_insert(self):
		"""Set action_by to current user"""
		if not self.action_by:
			self.action_by = frappe.session.user

		if not self.action_date:
			self.action_date = utils.now_datetime()

		# Get user's role
		if not self.role:
			self.role = self._get_user_approval_role()

	def _get_user_approval_role(self):
		"""Get the user's highest approval role"""
		user_roles = frappe.get_roles(self.action_by)

		if "Tax Report Approver" in user_roles:
			return "Tax Report Approver"
		elif "Tax Report Reviewer" in user_roles:
			return "Tax Report Reviewer"
		elif "Accounts Manager" in user_roles:
			return "Accounts Manager"
		elif "Accounts User" in user_roles:
			return "Accounts User"
		else:
			return "User"


def create_approval_log(report, action, from_status=None, to_status=None, comments=None):
	"""
	Create an approval log entry.

	Args:
		report: Name of the eTax Report
		action: Action performed (Created, Approved, Rejected, etc.)
		from_status: Previous status
		to_status: New status
		comments: Optional comments

	Returns:
		eTax Approval Log document
	"""
	log = frappe.get_doc({
		"doctype": "eTax Approval Log",
		"report": report,
		"action": action,
		"from_status": from_status,
		"to_status": to_status,
		"comments": comments
	})
	log.insert(ignore_permissions=True)
	frappe.db.commit()
	return log
