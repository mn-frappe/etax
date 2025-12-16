# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Database Indexes

Defines indexes for eTax DocTypes to improve query performance.
"""

import frappe


def setup_indexes():
	"""Create database indexes for eTax tables"""
	indexes = [
		# eTax Report indexes
		{
			"table": "tabeTax Report",
			"fields": ["report_no"],
			"name": "idx_etax_report_no"
		},
		{
			"table": "tabeTax Report",
			"fields": ["tax_report_code"],
			"name": "idx_etax_report_code"
		},
		{
			"table": "tabeTax Report",
			"fields": ["period_year", "period"],
			"name": "idx_etax_report_period"
		},
		{
			"table": "tabeTax Report",
			"fields": ["status"],
			"name": "idx_etax_report_status"
		},
		{
			"table": "tabeTax Report",
			"fields": ["ent_id"],
			"name": "idx_etax_report_ent"
		},
		
		# eTax Submission Log indexes
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
		
		# eTax Taxpayer indexes
		{
			"table": "tabeTax Taxpayer",
			"fields": ["ent_id"],
			"name": "idx_etax_taxpayer_ent"
		}
	]
	
	for idx in indexes:
		try:
			create_index(idx["table"], idx["fields"], idx["name"])
		except Exception as e:
			# Index might already exist
			pass


def create_index(table, fields, name):
	"""Create a database index"""
	if not frappe.db.table_exists(table):
		return
	
	# Check if index exists
	existing = frappe.db.sql("""
		SHOW INDEX FROM `{table}` WHERE Key_name = %s
	""".format(table=table), name)
	
	if existing:
		return
	
	# Create index
	field_list = ", ".join([f"`{f}`" for f in fields])
	frappe.db.sql("""
		CREATE INDEX `{name}` ON `{table}` ({fields})
	""".format(name=name, table=table, fields=field_list))
	
	frappe.db.commit()
