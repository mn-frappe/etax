# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eTax Installation Script

Called after app installation to set up:
- Default settings
- Custom fields (if needed)
- Indexes for performance
"""

import frappe


def after_install():
    """Run after eTax app is installed"""
    create_default_settings()
    setup_permissions()
    add_to_integrations_workspace()
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
    """Add eTax Settings to Integrations workspace under MN Settings section.

    Properly calculates idx to avoid conflicts with other apps.
    Also updates the content JSON which controls the visual layout.
    """
    import json

    if not frappe.db.exists("Workspace", "Integrations"):
        return

    workspace = frappe.get_doc("Workspace", "Integrations")

    # Get the maximum idx to avoid conflicts
    max_idx = max([link.idx or 0 for link in workspace.links] or [0])

    # Check if MN Settings section exists and eTax link exists
    mn_settings_idx = None
    etax_link_exists = False

    for link in workspace.links:
        if link.type == "Card Break" and link.label == "MN Settings":
            mn_settings_idx = link.idx
        if link.link_to == "eTax Settings":
            etax_link_exists = True

    # Already configured
    if etax_link_exists:
        return

    modified = False

    # Add MN Settings section if it doesn't exist
    if mn_settings_idx is None:
        max_idx += 1
        workspace.append("links", {
            "type": "Card Break",
            "label": "MN Settings",
            "idx": max_idx,
        })
        modified = True

    # Add eTax Settings link with proper idx
    max_idx = max([link.idx or 0 for link in workspace.links] or [0]) + 1
    workspace.append("links", {
        "type": "Link",
        "label": "eTax Settings",
        "link_to": "eTax Settings",
        "link_type": "DocType",
        "icon": "tax",
        "idx": max_idx,
    })
    modified = True

    # Update content JSON to include MN Settings card (controls visual layout)
    if workspace.content:
        content = json.loads(workspace.content)
        mn_card_in_content = any(
            item.get("data", {}).get("card_name") == "MN Settings"
            for item in content
            if item.get("type") == "card"
        )
        if not mn_card_in_content:
            # Add MN Settings card to content
            content.append({
                "id": frappe.generate_hash(length=10),
                "type": "card",
                "data": {"card_name": "MN Settings", "col": 4},
            })
            workspace.content = json.dumps(content)
            modified = True

    if modified:
        workspace.save()
        frappe.db.commit()

        # Clear bootinfo cache so changes appear without hard refresh
        frappe.cache.delete_key("bootinfo")

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
