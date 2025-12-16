# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eTax Database Indexes

Performance-critical indexes for eTax queries.
Significantly improves query performance for:
- Report lookups by various criteria
- Log queries
- Taxpayer lookups

Run after install:
    bench --site [sitename] execute etax.setup.indexes.setup_indexes
"""

import frappe


# Index definitions: (table, fields, name, unique)
INDEXES = [
	# eTax Report - Primary lookups
	{
		"table": "tabeTax Report",
		"fields": ["report_no"],
		"name": "idx_etax_report_no",
		"unique": True
	},
	{
		"table": "tabeTax Report",
		"fields": ["tax_report_code"],
		"name": "idx_etax_report_code"
	},
	# Composite index for period-based queries (most common)
	{
		"table": "tabeTax Report",
		"fields": ["period_year", "period", "status"],
		"name": "idx_etax_report_period_status"
	},
	{
		"table": "tabeTax Report",
		"fields": ["ent_id", "period_year"],
		"name": "idx_etax_report_ent_year"
	},
	{
		"table": "tabeTax Report",
		"fields": ["status", "return_due_date"],
		"name": "idx_etax_report_status_due"
	},
	# Covering index for list queries
	{
		"table": "tabeTax Report",
		"fields": ["ent_id", "status", "period_year", "period"],
		"name": "idx_etax_report_list"
	},
	
	# eTax Submission Log - For audit trails
	{
		"table": "tabeTax Submission Log",
		"fields": ["report"],
		"name": "idx_etax_log_report"
	},
	{
		"table": "tabeTax Submission Log",
		"fields": ["timestamp"],
		"name": "idx_etax_log_time"
	},
	{
		"table": "tabeTax Submission Log",
		"fields": ["action", "status"],
		"name": "idx_etax_log_action_status"
	},
	
	# eTax Taxpayer - Organization lookups
	{
		"table": "tabeTax Taxpayer",
		"fields": ["ent_id"],
		"name": "idx_etax_taxpayer_ent",
		"unique": True
	},
	{
		"table": "tabeTax Taxpayer",
		"fields": ["tin"],
		"name": "idx_etax_taxpayer_tin"
	},
	
	# eTax Report Data Item - Fast value lookups
	{
		"table": "tabeTax Report Data Item",
		"fields": ["parent"],
		"name": "idx_etax_data_parent"
	},
	{
		"table": "tabeTax Report Data Item",
		"fields": ["tag_id"],
		"name": "idx_etax_data_tag"
	}
]


def setup_indexes():
	"""Create all database indexes for eTax tables"""
	created = 0
	skipped = 0
	
	for idx in INDEXES:
		try:
			if create_index_safe(
				idx["table"], 
				idx["fields"], 
				idx["name"],
				idx.get("unique", False)
			):
				created += 1
			else:
				skipped += 1
		except Exception as e:
			frappe.log_error(f"Index creation failed: {idx['name']}: {str(e)}", "eTax Indexes")
	
	frappe.db.commit()
	return {"created": created, "skipped": skipped}


def create_index_safe(table, fields, name, unique=False):
	"""Create index if it doesn't exist"""
	if not frappe.db.table_exists(table):
		return False
	
	# Check if index exists
	if index_exists(table, name):
		return False
	
	# Create index
	field_list = ", ".join([f"`{f}`" for f in fields])
	unique_str = "UNIQUE " if unique else ""
	
	try:
		frappe.db.sql(f"""
			CREATE {unique_str}INDEX `{name}` ON `{table}` ({field_list})
		""")
		return True
	except Exception:
		return False


def index_exists(table, name):
	"""Check if index exists on table"""
	try:
		result = frappe.db.sql("""
			SHOW INDEX FROM `{table}` WHERE Key_name = %s
		""".format(table=table), name)
		return bool(result)
	except Exception:
		return False


def drop_index(table, name):
	"""Drop an index if it exists"""
	if not index_exists(table, name):
		return False
	
	try:
		frappe.db.sql(f"DROP INDEX `{name}` ON `{table}`")
		frappe.db.commit()
		return True
	except Exception:
		return False


def analyze_tables():
	"""Analyze tables for query optimization"""
	tables = [
		"tabeTax Report",
		"tabeTax Submission Log",
		"tabeTax Taxpayer",
		"tabeTax Report Data Item"
	]
	
	for table in tables:
		if frappe.db.table_exists(table):
			try:
				frappe.db.sql(f"ANALYZE TABLE `{table}`")
			except Exception:
				pass
	
	frappe.db.commit()
