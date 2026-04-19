"""Odontogram validation hook."""
import frappe

def validate_tooth_chart(doc, method=None):
    """Validate tooth chart data on encounter save."""
    for tooth in (doc.teeth or []):
        if not tooth.tooth_number:
            frappe.throw("Each tooth row must have a tooth number.")
