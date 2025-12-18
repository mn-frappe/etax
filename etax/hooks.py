# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax - Electronic Tax Reporting for Mongolia Tax Authority (MTA)

Works with ERPNext and all ERPNext-based apps:
- ERPNext Core: Sales Invoice, Purchase Invoice, GL Entry for VAT reporting
- Healthcare: Patient billing feeds into tax reports
- Education: Student fees feeds into tax reports
- Lending: Loan transactions for tax reporting

eTax aggregates data from ERPNext's accounting module for:
- VAT Returns (НӨАТ тайлан)
- Corporate Tax Returns (ААНОАТ)
- Income Tax Reports
"""

app_name = "etax"
app_title = "eTax"
app_publisher = "Digital Consulting Service LLC (Mongolia)"
app_description = (
    "Electronic Tax Reporting for Mongolia Tax Authority (MTA). "
    "Works with ERPNext and all accounting transactions from Healthcare, Education, Lending."
)
app_email = "dev@frappe.mn"
app_license = "gpl-3.0"
app_version = "1.1.0"

# Required Apps - ERPNext required for accounting data
required_apps = ["frappe", "erpnext"]

# Installation hooks
after_install = "etax.setup.install.after_install"
before_uninstall = "etax.setup.install.before_uninstall"
after_migrate = ["etax.setup.install.after_migrate"]

# Error Reporting / Telemetry
# ---------------------------
# Reports unhandled exceptions to GitHub Issues (if enabled in settings)
exception_handler = "etax.etax.telemetry.on_error"

# Fixtures
# --------
# Approval workflow fixtures (order matters: states before workflow)
fixtures = [
    "etax/fixtures/etax_workflow_states.json",
    "etax/fixtures/etax_roles.json",
    "etax/fixtures/etax_workflow.json",
    "etax/fixtures/etax_notifications.json",
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/etax/css/etax.css"
# app_include_js = "/assets/etax/js/etax.js"

# include js, css files in header of web template
# web_include_css = "/assets/etax/css/etax.css"
# web_include_js = "/assets/etax/js/etax.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "etax/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "etax/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "etax.utils.jinja_methods",
# 	"filters": "etax.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "etax.setup.install.before_uninstall"
after_install = "etax.setup.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "etax.uninstall.before_uninstall"
# after_uninstall = "etax.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "etax.utils.before_app_install"
# after_app_install = "etax.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "etax.utils.before_app_uninstall"
# after_app_uninstall = "etax.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "etax.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"eTax Settings": {
		"on_update": "etax.api.cache.on_settings_update"
	},
	"eTax Report": {
		"after_insert": "etax.api.cache.on_report_sync",
		"on_update": "etax.api.cache.on_report_sync"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"etax.tasks.all"
# 	],
# 	"daily": [
# 		"etax.tasks.daily.run"
# 	],
# 	"hourly": [
# 		"etax.tasks.hourly"
# 	],
# 	"weekly": [
# 		"etax.tasks.weekly"
# 	],
# 	"monthly": [
# 		"etax.tasks.monthly"
# 	],
# }

scheduler_events = {
	"hourly": [
		"etax.performance.auto_sync_tax_reports",
	],
	"daily": [
		"etax.tasks.daily.sync_reports_daily",
	],
	"weekly": [
		"etax.performance.ensure_indexes",
	],
}

# Testing
# -------

# before_tests = "etax.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "etax.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "etax.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["etax.utils.before_request"]
# after_request = ["etax.utils.after_request"]

# Job Events
# ----------
# before_job = ["etax.utils.before_job"]
# after_job = ["etax.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"etax.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

