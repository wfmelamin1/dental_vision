"""
auto_billing.py
DentalVision Pro – Automated Billing Module
Handles: Invoice creation, insurance claim generation, payment allocation
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt


# ─────────────────────────────────────────────
# API Endpoints (whitelisted for JS calls)
# ─────────────────────────────────────────────

@frappe.whitelist()
def create_invoice_on_encounter_submit(doc, method=None):
    """
    Hook: Called when a Dental Encounter is submitted.
    Automatically creates a Sales Invoice for all completed procedures.
    """
    if isinstance(doc, str):
        doc = frappe.get_doc("Dental Encounter", doc)

    completed = [p for p in doc.procedures if p.status == "Completed" and not p.billed_to_invoice]
    if not completed:
        return

    customer_name = _get_or_create_customer(doc.patient)
    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = customer_name
    invoice.posting_date = doc.encounter_date or nowdate()
    invoice.due_date = doc.encounter_date or nowdate()
    invoice.set("custom_dental_encounter", doc.name)
    invoice.items = []

    for proc in completed:
        item_code = _resolve_item_code(proc.procedure_code)
        invoice.append("items", {
            "item_code":   item_code,
            "item_name":   f"[{proc.procedure_code}] {proc.procedure_name}",
            "description": _build_line_description(proc),
            "qty":         1,
            "rate":        flt(proc.fee),
            "amount":      flt(proc.fee),
        })

    invoice.flags.ignore_permissions = True
    invoice.save()

    # Mark procedures as billed
    frappe.db.set_value("Dental Encounter", doc.name, "sales_invoice", invoice.name)
    for proc in completed:
        frappe.db.set_value(
            "Encounter Procedure", proc.name,
            {"billed_to_invoice": 1, "invoice_row_ref": invoice.name},
            update_modified=False
        )

    frappe.msgprint(
        _("Sales Invoice {0} created for {1} procedure(s).").format(
            frappe.bold(invoice.name), len(completed)
        ),
        alert=True
    )
    return invoice.name


@frappe.whitelist()
def cancel_invoice_on_encounter_cancel(doc, method=None):
    """Hook: Cancel the linked Sales Invoice when an encounter is cancelled."""
    if isinstance(doc, str):
        doc = frappe.get_doc("Dental Encounter", doc)

    if doc.sales_invoice:
        inv = frappe.get_doc("Sales Invoice", doc.sales_invoice)
        if inv.docstatus == 1:
            inv.cancel()
            frappe.msgprint(_(f"Sales Invoice {doc.sales_invoice} cancelled."), alert=True)


@frappe.whitelist()
def generate_insurance_claim(encounter_name: str):
    """
    Manually triggered: Generate an Insurance Claim document for an encounter.
    Call from the Dental Encounter form button.
    """
    enc = frappe.get_doc("Dental Encounter", encounter_name)
    patient = frappe.get_doc("Patient", enc.patient)

    if not patient.primary_insurance_provider:
        frappe.throw(_("Patient has no primary insurance provider on file."))

    claim = frappe.new_doc("Insurance Claim")
    claim.patient = enc.patient
    claim.dental_encounter = encounter_name
    claim.insurance_provider = patient.primary_insurance_provider
    claim.insurance_member_id = patient.primary_insurance_id
    claim.group_number = patient.primary_group_number
    claim.provider = enc.provider
    claim.date_of_service = enc.encounter_date
    claim.claim_status = "Draft"

    # Add procedures to claim
    for proc in enc.procedures:
        if proc.status == "Completed":
            claim.append("claim_procedures", {
                "cdt_code": proc.procedure_code,
                "procedure_name": proc.procedure_name,
                "tooth_number": proc.tooth_number,
                "surface": proc.surface,
                "fee": proc.fee,
                "estimated_coverage": proc.insurance_estimate,
            })

    claim.save()
    frappe.db.set_value("Dental Encounter", encounter_name, "insurance_claim", claim.name)
    frappe.msgprint(_(f"Insurance Claim {claim.name} created."), alert=True)
    return claim.name


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def _get_or_create_customer(patient_name: str) -> str:
    patient = frappe.get_doc("Patient", patient_name)
    existing = frappe.db.get_value(
        "Customer", {"customer_name": patient.full_name}, "name"
    )
    if existing:
        return existing

    customer = frappe.new_doc("Customer")
    customer.customer_name = patient.full_name
    customer.customer_type = "Individual"
    customer.customer_group = frappe.db.get_single_value(
        "Dental Vision Settings", "default_customer_group"
    ) or "Dental Patients"
    customer.territory = "All Territories"
    customer.flags.ignore_permissions = True
    customer.save()
    return customer.name


def _resolve_item_code(cdt_code: str) -> str:
    """Get or create an ERPNext Item for a CDT code."""
    proc = frappe.get_doc("Procedure Code", cdt_code)
    if proc.linked_item and frappe.db.exists("Item", proc.linked_item):
        return proc.linked_item

    item_code = f"CDT-{cdt_code}"
    if not frappe.db.exists("Item", item_code):
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.item_name = proc.procedure_name
        item.item_group = "Dental Services"
        item.stock_uom = "Nos"
        item.is_stock_item = 0
        item.is_sales_item = 1
        item.standard_rate = flt(proc.standard_fee)
        item.flags.ignore_permissions = True
        item.save()
        frappe.db.set_value("Procedure Code", cdt_code, "linked_item", item_code)

    return item_code


def _build_line_description(proc) -> str:
    parts = [f"CDT: {proc.procedure_code}"]
    if proc.tooth_number:
        parts.append(f"Tooth: #{proc.tooth_number}")
    if proc.surface:
        parts.append(f"Surface: {proc.surface}")
    if proc.quadrant:
        parts.append(f"Quadrant: {proc.quadrant}")
    return " | ".join(parts)


# ─────────────────────────────────────────────
# Insurance Claim Submission Hook
# ─────────────────────────────────────────────

def submit_insurance_claim(doc, method=None):
    """
    Called when a Sales Invoice is submitted.
    Auto-submit the linked Insurance Claim if it's in Draft state.
    """
    encounter_name = frappe.db.get_value(
        "Dental Encounter", {"sales_invoice": doc.name}, "name"
    )
    if not encounter_name:
        return

    claim_name = frappe.db.get_value("Dental Encounter", encounter_name, "insurance_claim")
    if claim_name:
        claim = frappe.get_doc("Insurance Claim", claim_name)
        if claim.claim_status == "Draft":
            claim.claim_status = "Submitted"
            claim.submission_date = nowdate()
            claim.save()
