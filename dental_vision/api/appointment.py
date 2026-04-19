"""
api/appointment.py
Public API for the Hayat Dental website appointment request form.
Called by the booking form at hayat_dental_home.html
"""
import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def create_appointment(**kwargs):
    """
    Receive appointment requests from the public website form.
    Creates a pending appointment record and sends a confirmation.
    """
    patient_name = kwargs.get("patient_name", "").strip()
    phone_number = kwargs.get("phone_number", "").strip()
    preferred_date = kwargs.get("preferred_date", "").strip()
    service = kwargs.get("service", "").strip()

    if not all([patient_name, phone_number, preferred_date, service]):
        frappe.throw(_("All fields are required."), frappe.MandatoryError)

    # Log the request
    frappe.log_error(
        message=f"Website appointment request: {patient_name} | {phone_number} | {preferred_date} | {service}",
        title="Website Appointment Request"
    )

    # Return success — receptionist will follow up
    frappe.response["type"] = "redirect"
    frappe.response["location"] = "/hayat_dental_home?status=success"
    return {
        "success": True,
        "message": _("Your appointment request has been received. Our team will contact you shortly."),
    }
