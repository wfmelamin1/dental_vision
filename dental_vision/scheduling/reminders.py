"""Appointment reminder hooks."""
import frappe
from frappe.utils import add_days, nowdate

def schedule_confirmation(doc, method=None):
    pass

def handle_status_change(doc, method=None):
    pass

def send_appointment_reminders():
    """Daily job: remind patients of tomorrow's appointments."""
    tomorrow = add_days(nowdate(), 1)
    appts = frappe.get_list(
        "Appointment",
        filters={"appointment_date": tomorrow, "appointment_status": ["in", ["Scheduled", "Confirmed"]]},
        fields=["name", "patient", "patient_name", "start_time", "provider"]
    )
    for appt in appts:
        patient_email = frappe.db.get_value("Patient", appt.patient, "email")
        if patient_email:
            frappe.sendmail(
                recipients=[patient_email],
                subject="Appointment Reminder — Tomorrow",
                message=f"Dear {appt.patient_name}, this is a reminder of your appointment tomorrow at {appt.start_time}.",
            )
