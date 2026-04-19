"""
clinical/treatment_plan.py
Enforces BRD Rule: Only ONE Active treatment plan per patient at a time (Section 6.2.3)
"""
import frappe
from frappe import _


def enforce_single_active_plan(doc, method=None):
    """
    BRD Rule: Only one plan of type Active per patient.
    On setting Active → deactivate existing Active plan.
    """
    if doc.status not in ("Patient Accepted", "In Progress"):
        return

    # Find other active plans for this patient
    existing = frappe.get_all(
        "Treatment Plan",
        filters={
            "patient": doc.patient,
            "status": ["in", ["Patient Accepted", "In Progress"]],
            "name": ["!=", doc.name],
            "docstatus": ["!=", 2],
        },
        fields=["name", "plan_date"]
    )

    for plan in existing:
        frappe.db.set_value("Treatment Plan", plan.name, "status", "Draft")
        frappe.msgprint(
            _(f"Treatment Plan {plan.name} was deactivated. Only one active plan allowed per patient."),
            alert=True
        )
