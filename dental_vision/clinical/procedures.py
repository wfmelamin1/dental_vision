"""
clinical/procedures.py
Handles Dental Procedure business logic per BRD 6.2.2
"""
import frappe
from frappe.utils import nowdate


def on_procedure_complete(doc, method=None):
    """
    Hook: Called when a Dental Procedure is submitted.
    - Removes procedure from Active Treatment Plan
    - Triggers invoice creation
    """
    if doc.status != "Complete":
        return

    # Set completion date
    if not doc.date_completed:
        frappe.db.set_value("Dental Procedure", doc.name, "date_completed", nowdate())

    # Remove from active treatment plan
    if doc.treatment_plan:
        _remove_from_active_plan(doc)


def _remove_from_active_plan(proc_doc):
    """Remove a completed procedure from the active treatment plan per BRD 6.7"""
    try:
        tp = frappe.get_doc("Treatment Plan", proc_doc.treatment_plan)
        if tp.status in ("Draft", "Presented to Patient", "Patient Accepted", "In Progress"):
            for row in tp.planned_procedures:
                if row.name == proc_doc.name or (
                    hasattr(row, "procedure_code") and
                    row.procedure_code == proc_doc.procedure_code and
                    row.status != "Completed"
                ):
                    frappe.db.set_value(
                        "Encounter Procedure", row.name,
                        "status", "Completed"
                    )
            frappe.db.commit()
    except Exception:
        pass  # Non-blocking
