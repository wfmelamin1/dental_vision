"""Insurance claim hooks."""
import frappe
from frappe.utils import nowdate

def submit_insurance_claim(doc, method=None):
    """Called on Sales Invoice submit — advance linked claim to Submitted."""
    encounter_name = frappe.db.get_value(
        "Dental Encounter", {"sales_invoice": doc.name}, "name"
    )
    if not encounter_name:
        return
    claim_name = frappe.db.get_value("Dental Encounter", encounter_name, "insurance_claim")
    if claim_name:
        frappe.db.set_value("Insurance Claim", claim_name, {
            "claim_status": "Submitted",
            "submission_date": nowdate()
        })

def follow_up_unpaid_claims():
    """Monthly job: flag claims pending > 45 days."""
    pass
