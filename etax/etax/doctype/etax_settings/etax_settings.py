# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
eTax Settings DocType

Manages configuration for eTax (Electronic Tax Report System) API integration.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class eTaxSettings(Document):
	"""
	eTax Settings - Configuration for Mongolia Tax Authority API

	API Environments:
	- Staging: st-etax.mta.mn (for testing)
	- Production: etax.mta.mn (for live tax reports)

	Authentication:
	- Uses ITC OAuth2 (same provider as eBalance)
	- Requires NE-KEY header for all API calls
	"""

	# API URLs by environment
	API_URLS = {
		"Staging": "https://st-etax.mta.mn/api/beta",
		"Production": "https://etax.mta.mn/api/beta"
	}

	AUTH_URLS = {
		"Staging": "https://api.frappe.mn/auth/itc-staging",
		"Production": "https://api.frappe.mn/auth/itc"
	}

	def validate(self):
		"""Validate settings before save"""
		self.update_api_urls()

		if self.enabled:
			self.validate_credentials()

	def update_api_urls(self):
		"""Auto-update API URLs based on environment"""
		env = self.environment or "Staging"
		self.api_base_url = self.API_URLS.get(env, self.API_URLS["Staging"])
		self.auth_url = self.AUTH_URLS.get(env, self.AUTH_URLS["Staging"])

	def validate_credentials(self):
		"""Validate required credentials are present"""
		if not self.username:
			frappe.throw(_("Username is required"))
		if not self.password:
			frappe.throw(_("Password is required"))
		if not self.ne_key:
			frappe.throw(_("NE-KEY is required. Request from request@itc.gov.mn"))
		if not self.org_regno:
			frappe.throw(_("Organization Registry Number is required"))

	def on_update(self):
		"""Clear cached settings after update"""
		frappe.cache.delete_value("etax_settings")

	@frappe.whitelist()
	def test_connection(self):
		"""
		Test API connection and fetch organization info.

		Returns:
			dict: Connection status and organization details
		"""
		if not self.enabled:
			return {"success": False, "message": _("eTax integration is not enabled")}

		try:
			from etax.api.client import ETaxClient

			client = ETaxClient(self)
			all_orgs = client.get_user_orgs(skip_cache=True)

			if all_orgs:
				# Find the organization matching configured org_regno
				org = None
				if self.org_regno:
					for o in all_orgs:
						# Match by pin (registry number)
						if str(o.get("pin", "")) == str(self.org_regno):
							org = o
							break

				if not org:
					# No matching org found - show available options
					available_orgs = [f"{o.get('pin')}: {o.get('entityName')}" for o in all_orgs[:5]]
					return {
						"success": False,
						"message": _("Organization with RegNo '{0}' not found. Available organizations: {1}").format(
							self.org_regno,
							", ".join(available_orgs)
						)
					}

				# Update organization info from matched org
				self.org_name = org.get("entityName", "").strip()
				self.taxpayer_tin = org.get("tin", "")
				self.ent_id = org.get("id")  # Store entity ID for API calls
				self.connection_status = "Connected"

				ent_type = org.get("entType")
				if ent_type == 1:
					self.taxpayer_type = "1 - Individual"
				elif ent_type == 2:
					self.taxpayer_type = "2 - Legal Entity"

				self.save()

				return {
					"success": True,
					"message": _("Connection successful"),
					"org_name": self.org_name,
					"taxpayer_tin": self.taxpayer_tin
				}

			# Authentication succeeded but no organizations linked
			self.connection_status = "Auth OK - No Orgs"
			self.save()
			return {
				"success": True,
				"message": _("Authentication successful! No taxpayer organizations linked to this account. Please register your organization (TIN) at st-etax.mta.mn first."),
				"warning": True
			}

		except Exception as e:
			self.connection_status = "Failed"
			self.save()
			frappe.log_error(f"eTax connection test failed: {e!s}", "eTax")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_reports(self):
		"""
		Sync pending tax reports from MTA.

		Returns:
			dict: Sync status and count of synced reports
		"""
		if not self.enabled:
			return {"success": False, "message": _("eTax integration is not enabled")}

		try:
			from etax.api.client import ETaxClient

			client = ETaxClient(self)

			# Get pending reports
			reports = client.get_report_list()

			synced = 0
			for report in reports:
				# Create or update eTax Report
				self._sync_report(report)
				synced += 1

			# Update last sync time
			self.last_sync = frappe.utils.now()
			self.save()

			return {
				"success": True,
				"message": _("Synced {0} reports").format(synced),
				"count": synced
			}

		except Exception as e:
			frappe.log_error(f"eTax sync failed: {e!s}", "eTax")
			return {"success": False, "message": str(e)}

	def _sync_report(self, report_data):
		"""Sync a single report from API data"""
		from etax.api.transformer import ETaxTransformer

		transformer = ETaxTransformer()
		doc_data = transformer.api_to_report(report_data)

		# Check if report exists
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

		return doc

	def get_status_html(self):
		"""Generate status HTML for display"""
		if not self.enabled:
			return """
			<div class="alert alert-warning">
				<i class="fa fa-warning"></i> eTax integration is disabled
			</div>
			"""

		status_class = "success" if self.access_token else "warning"
		status_text = _("Connected") if self.access_token else _("Not Connected")

		return f"""
		<div class="alert alert-{status_class}">
			<strong>{_("Status")}:</strong> {status_text}<br>
			<strong>{_("Environment")}:</strong> {self.environment}<br>
			<strong>{_("Organization")}:</strong> {self.org_name or '-'}<br>
			<strong>{_("Last Sync")}:</strong> {self.last_sync or _('Never')}
		</div>
		"""


def get_etax_settings():
	"""Get eTax Settings singleton with caching"""
	settings = frappe.cache.get_value("etax_settings")
	if not settings:
		settings = frappe.get_single("eTax Settings")
		frappe.cache.set_value("etax_settings", settings)
	return settings
