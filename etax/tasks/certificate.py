# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Certificate management tasks for eTax

Per eTax API documentation, digital certificates are required for:
- Signing tax reports before submission
- Authentication with MTA (Mongolia Tax Authority)

This module handles:
- Certificate expiry checking
- Email alerts before certificate expiration
- Certificate validation on upload
"""

import frappe
from frappe import _
from frappe.utils import getdate, date_diff, cint


def check_certificate_expiry():
    """
    Daily task to check certificate expiry and send alerts

    Checks if the digital certificate is expiring soon and sends
    email alerts based on the configured alert_days setting.
    """
    if not frappe.db.get_single_value("eTax Settings", "enabled"):
        return

    settings = frappe.get_cached_doc("eTax Settings")

    # Check if certificate is configured
    if not settings.get("certificate_file"):
        return

    cert_expiry = settings.get("certificate_expiry")
    if not cert_expiry:
        # Try to extract expiry from certificate
        try:
            cert_expiry = extract_certificate_expiry(settings)
            if cert_expiry:
                frappe.db.set_single_value("eTax Settings", "certificate_expiry", str(cert_expiry))
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title="eTax Certificate Expiry Extraction Failed"
            )
            return

    if not cert_expiry:
        return

    # Calculate days until expiry
    cert_expiry_date = getdate(str(cert_expiry) if cert_expiry else None)
    today = getdate()
    if cert_expiry_date and today:
        days_until_expiry = date_diff(cert_expiry_date, today)
    else:
        return

    alert_days = cint(str(settings.get("cert_expiry_alert_days")) if settings.get("cert_expiry_alert_days") else "30") or 30

    frappe.logger("etax").info(
        f"Certificate expiry check: {days_until_expiry} days remaining "
        f"(expiry: {cert_expiry}, alert threshold: {alert_days} days)"
    )

    # Check if we need to send an alert
    if days_until_expiry <= 0:
        # Certificate has expired!
        send_certificate_alert(
            settings,
            subject=f"URGENT: eTax Certificate EXPIRED!",
            days_remaining=days_until_expiry,
            is_expired=True
        )
    elif days_until_expiry <= alert_days:
        # Certificate expiring soon
        send_certificate_alert(
            settings,
            subject=f"eTax Certificate Expiring in {days_until_expiry} days",
            days_remaining=days_until_expiry,
            is_expired=False
        )


def extract_certificate_expiry(settings):
    """
    Extract expiry date from a PKCS#12 certificate file

    Args:
        settings: eTax Settings document

    Returns:
        date: Certificate expiry date or None
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import pkcs12

    cert_file_path = settings.get("certificate_file")
    if not cert_file_path:
        return None

    # Get file content from File doctype
    file_docs = frappe.get_all("File", filters={"file_url": cert_file_path}, limit=1)
    if not file_docs:
        frappe.log_error(
            message=f"Certificate file not found: {cert_file_path}",
            title="eTax Certificate File Missing"
        )
        return None

    try:
        file_doc = frappe.get_doc("File", file_docs[0].name)
        # Read the file content - use getattr for File document method
        get_full_path = getattr(file_doc, "get_full_path", None)
        if not get_full_path:
            frappe.log_error(
                message="File document missing get_full_path method",
                title="eTax Certificate Error"
            )
            return None
        file_path = get_full_path()
        with open(file_path, "rb") as f:
            cert_data = f.read()

        # Get certificate password
        cert_password = settings.get_password("certificate_password")
        if cert_password:
            cert_password = cert_password.encode()
        else:
            cert_password = None

        # Load PKCS#12 certificate
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            cert_data,
            cert_password,
            default_backend()
        )

        if certificate:
            # Extract expiry date
            expiry = certificate.not_valid_after_utc
            return getdate(expiry)

    except Exception as e:
        frappe.log_error(
            message=f"Failed to extract certificate expiry: {e}",
            title="eTax Certificate Parsing Failed"
        )

    return None


def send_certificate_alert(settings, subject, days_remaining, is_expired=False):
    """
    Send email alert about certificate expiry

    Args:
        settings: eTax Settings document
        subject: Email subject
        days_remaining: Days until expiry (negative if expired)
        is_expired: Whether certificate has already expired
    """
    notify_email = settings.get("notify_email")
    if not notify_email:
        # Fall back to system manager email
        notify_email = frappe.db.get_single_value("System Settings", "admin_email")

    if not notify_email:
        frappe.logger("etax").warning(
            f"Certificate alert: {subject} - No email configured!"
        )
        return

    cert_expiry = settings.get("certificate_expiry")
    org_name = settings.get("org_name") or "Your Organization"
    org_regno = settings.get("org_regno") or "N/A"

    if is_expired:
        status_html = """
        <div style="background-color: #dc3545; color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <strong>⛔ CERTIFICATE HAS EXPIRED</strong>
            <p>Your eTax digital certificate has expired. You cannot submit tax reports until you renew it.</p>
        </div>
        """
        action_html = """
        <p><strong>Immediate Action Required:</strong></p>
        <ol>
            <li>Contact the certificate issuer to renew your certificate</li>
            <li>Upload the new certificate in eTax Settings</li>
            <li>Test the connection before submitting reports</li>
        </ol>
        """
    else:
        status_html = f"""
        <div style="background-color: #ffc107; color: black; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <strong>⚠️ CERTIFICATE EXPIRING SOON</strong>
            <p>Your eTax digital certificate will expire in <strong>{days_remaining} days</strong>.</p>
        </div>
        """
        action_html = """
        <p><strong>Recommended Action:</strong></p>
        <ol>
            <li>Begin the certificate renewal process now to avoid disruption</li>
            <li>Contact your certificate issuer for renewal instructions</li>
            <li>Upload the new certificate before the current one expires</li>
        </ol>
        """

    message = f"""
    <h3>eTax Digital Certificate Alert</h3>

    {status_html}

    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
        <tr><td><strong>Organization:</strong></td><td>{org_name}</td></tr>
        <tr><td><strong>Registry Number:</strong></td><td>{org_regno}</td></tr>
        <tr><td><strong>Certificate Expiry:</strong></td><td>{cert_expiry}</td></tr>
        <tr><td><strong>Days Remaining:</strong></td><td>{days_remaining}</td></tr>
    </table>

    {action_html}

    <p style="color: #666; font-size: 12px; margin-top: 20px;">
        This is an automated message from eTax Integration.<br>
        Configure alert settings in: eTax Settings → Certificate Section
    </p>
    """

    try:
        frappe.sendmail(
            recipients=[notify_email],
            subject=subject,
            message=message,
            now=True
        )
        frappe.logger("etax").info(f"Certificate expiry alert sent to {notify_email}")
    except Exception as e:
        frappe.log_error(
            message=f"Failed to send certificate alert: {e}",
            title="eTax Certificate Alert Failed"
        )


def validate_certificate(certificate_file, password):
    """
    Validate a PKCS#12 certificate file

    Args:
        certificate_file: File path or URL
        password: Certificate password

    Returns:
        dict: Certificate info (subject, expiry, issuer) or error
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import pkcs12

    try:
        # Get file content
        file_docs = frappe.get_all("File", filters={"file_url": certificate_file}, limit=1)
        if not file_docs:
            return {"success": False, "error": "Certificate file not found"}

        file_doc = frappe.get_doc("File", file_docs[0].name)
        # Use getattr for File document method
        get_full_path = getattr(file_doc, "get_full_path", None)
        if not get_full_path:
            return {"success": False, "error": "File document missing get_full_path method"}
        file_path = get_full_path()
        with open(file_path, "rb") as f:
            cert_data = f.read()

        # Encode password if provided
        if password:
            password = password.encode()

        # Load and validate certificate
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            cert_data,
            password,
            default_backend()
        )

        if not certificate:
            return {"success": False, "error": "No certificate found in file"}

        if not private_key:
            return {"success": False, "error": "No private key found - cannot sign documents"}

        # Extract certificate info
        subject = certificate.subject.rfc4514_string()
        issuer = certificate.issuer.rfc4514_string()
        expiry = certificate.not_valid_after_utc
        valid_from = certificate.not_valid_before_utc

        expiry_date = getdate(expiry)
        today = getdate()
        days_remaining = 0
        if expiry_date and today:
            days_remaining = date_diff(expiry_date, today)

        return {
            "success": True,
            "subject": subject,
            "issuer": issuer,
            "valid_from": str(valid_from),
            "expiry": str(expiry),
            "expiry_date": expiry_date,
            "days_remaining": days_remaining
        }

    except ValueError as e:
        return {"success": False, "error": f"Invalid password or corrupt certificate: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Certificate validation failed: {e}"}


@frappe.whitelist()
def validate_certificate_api(certificate_file=None, password=None):
    """
    API endpoint to validate certificate from eTax Settings

    Returns certificate info or error message
    """
    frappe.only_for(["System Manager", "Accounts Manager"])

    if not certificate_file:
        settings = frappe.get_doc("eTax Settings")
        certificate_file = settings.get("certificate_file")
        password = settings.get_password("certificate_password")

    if not certificate_file:
        return {"success": False, "error": "No certificate file configured"}

    result = validate_certificate(certificate_file, password)

    if result.get("success"):
        # Update expiry in settings
        frappe.db.set_single_value("eTax Settings", "certificate_expiry", result.get("expiry_date"))
        frappe.db.commit()

    return result
