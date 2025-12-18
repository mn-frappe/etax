# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eTax Daily Tasks

Scheduled tasks that run daily.
"""

import frappe


def sync_reports_daily():
    """
    Daily task to sync tax reports from MTA.

    Only runs if:
    - eTax is enabled
    - Auto sync is enabled
    - Sync frequency is Daily
    """
    try:
        settings = frappe.get_single("eTax Settings")

        if not settings.enabled:
            return

        if not settings.auto_sync_reports:
            return

        if settings.sync_frequency != "Daily":
            return

        # Run sync
        result = settings.sync_reports()

        if result.get("success"):
            frappe.logger().info(f"eTax daily sync: {result.get('count', 0)} reports synced")
        else:
            frappe.logger().error(f"eTax daily sync failed: {result.get('message')}")

    except Exception as e:
        frappe.log_error(f"eTax daily sync error: {e!s}", "eTax Scheduler")
