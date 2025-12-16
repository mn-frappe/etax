# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Installation Script

Called after app installation to set up:
- Default settings
- Custom fields (if needed)
- Indexes for performance
"""

import frappe
from frappe import _


def after_install():
	"""Run after eTax app is installed"""
	create_default_settings()
	setup_permissions()
	frappe.db.commit()
	print("eTax app installed successfully!")


def create_default_settings():
	"""Create default eTax Settings if not exists"""
	if not frappe.db.exists("DocType", "eTax Settings"):
		return
	
	settings = frappe.get_single("eTax Settings")
	needs_save = False
	
	# Set defaults if empty
	if not settings.environment:
		settings.environment = "Staging"
		needs_save = True
	
	if not settings.timeout:
		settings.timeout = 30
		needs_save = True
	
	if not settings.api_base_url:
		settings.api_base_url = "https://st-etax.mta.mn/api/beta"
		needs_save = True
	
	if not settings.auth_url:
		settings.auth_url = "https://api.frappe.mn/auth/itc-staging"
		needs_save = True
	
	if needs_save:
		# Use db_set to avoid validation issues with missing credentials
		frappe.db.set_single_value("eTax Settings", "environment", settings.environment)
		frappe.db.set_single_value("eTax Settings", "timeout", settings.timeout)
		frappe.db.set_single_value("eTax Settings", "api_base_url", settings.api_base_url)
		frappe.db.set_single_value("eTax Settings", "auth_url", settings.auth_url)


def setup_permissions():
	"""Set up role permissions for eTax DocTypes"""
	# Permissions are defined in DocType JSON files
	pass


def after_migrate():
	"""Run after migration to set up workspace integration"""
	add_to_integrations_workspace()
	frappe.db.commit()


def add_to_integrations_workspace():
	"""Add eTax Settings to Integrations workspace under MN Settings section"""
	if not frappe.db.exists("Workspace", "Integrations"):
		return
	
	workspace = frappe.get_doc("Workspace", "Integrations")
	
	# Check if MN Settings section exists
	mn_settings_exists = False
	etax_link_exists = False
	mn_settings_idx = -1
	
	for i, link in enumerate(workspace.links):
		if link.type == "Card Break" and link.label == "MN Settings":
			mn_settings_exists = True
			mn_settings_idx = i
		if link.link_to == "eTax Settings":
			etax_link_exists = True
	
	# Already configured
	if etax_link_exists:
		return
	
	modified = False
	
	# Add MN Settings section if it doesn't exist
	if not mn_settings_exists:
		workspace.append("links", {
			"type": "Card Break",
			"label": "MN Settings"
		})
		modified = True
	
	# Add eTax Settings link
	workspace.append("links", {
		"type": "Link",
		"label": "eTax Settings",
		"link_to": "eTax Settings",
		"link_type": "DocType",
		"icon": "tax"
	})
	modified = True
	
	if modified:
		workspace.save()
		print("  ✓ Added eTax Settings to Integrations workspace (MN Settings section)")


def before_uninstall():
	"""Run before eTax app is uninstalled"""
	print("Preparing to uninstall eTax app...")
	remove_from_integrations_workspace()


def remove_from_integrations_workspace():
	"""Remove eTax Settings from Integrations workspace"""
	if not frappe.db.exists("Workspace", "Integrations"):
		return
	
	workspace = frappe.get_doc("Workspace", "Integrations")
	workspace.links = [link for link in workspace.links if link.link_to != "eTax Settings"]
	workspace.save()


def after_uninstall():
	"""Run after eTax app is uninstalled"""
	# Clean up any custom fields if needed
	pass
