"""Recall reminder scheduler."""
import frappe
from frappe.utils import add_days, nowdate

def send_recall_reminders():
    """Daily job: email patients whose recall date is in 30 days."""
    due = frappe.get_list(
        "Patient",
        filters={"patient_status": "Active", "next_recall_date": add_days(nowdate(), 30)},
        fields=["name", "full_name", "email", "next_recall_date"]
    )
    for patient in due:
        if patient.email:
            frappe.sendmail(
                recipients=[patient.email],
                subject="Your Dental Recall is Due Soon",
                message=f"Dear {patient.full_name}, your recall appointment is due on {patient.next_recall_date}. Please call us to schedule.",
            )
