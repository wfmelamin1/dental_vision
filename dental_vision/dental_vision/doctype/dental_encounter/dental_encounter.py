"""
dental_encounter.py
Phase 2: Clinical Logic Controller
Handles odontogram state management and automatic billing triggers.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, flt, getdate
from frappe.utils import now_datetime as nowdatetime
import json


class DentalEncounter(Document):

    # ─────────────────────────────────────────────
    # Lifecycle Hooks
    # ─────────────────────────────────────────────

    def validate(self):
        self.validate_patient()
        self.calculate_totals()
        self.update_tooth_states()
        self.set_audit_timestamps()

    def on_submit(self):
        self.create_or_update_sales_invoice()
        self.update_patient_last_visit()
        self.finalize_odontogram_snapshot()

    def on_cancel(self):
        self.cancel_linked_invoice()

    def before_save(self):
        self.full_name_from_patient()

    # ─────────────────────────────────────────────
    # Validation Methods
    # ─────────────────────────────────────────────

    def validate_patient(self):
        if not self.patient:
            frappe.throw(_("Patient is required"))
        patient_doc = frappe.get_doc("Patient", self.patient)
        if patient_doc.patient_status in ("Deceased", "Archived"):
            frappe.throw(_(f"Cannot create encounter for {patient_doc.patient_status} patient."))

    def full_name_from_patient(self):
        if self.patient and not self.patient_name:
            self.patient_name = frappe.db.get_value("Patient", self.patient, "full_name")

    def calculate_totals(self):
        total_fee = 0.0
        insurance_total = 0.0
        patient_total = 0.0
        for proc in self.procedures:
            total_fee += flt(proc.fee)
            insurance_total += flt(proc.insurance_estimate)
            patient_total += flt(proc.patient_estimate)
        self.total_fee = total_fee
        self.insurance_portion = insurance_total
        self.patient_portion = patient_total

    def set_audit_timestamps(self):
        for tooth in self.teeth:
            if tooth.has_value_changed("overall_condition") or tooth.has_value_changed("mesial"):
                tooth.last_updated_by = frappe.session.user
                tooth.last_updated_on = nowdatetime()

    # ─────────────────────────────────────────────
    # Odontogram / Tooth State Management
    # ─────────────────────────────────────────────

    def update_tooth_states(self):
        """Sync the SVG JSON state for each tooth based on its surface conditions."""
        for tooth in self.teeth:
            odontogram = OdontogramLogic(tooth)
            tooth.svg_state_json = json.dumps(odontogram.compute_svg_state())

    def get_tooth_by_number(self, tooth_number: str):
        for tooth in self.teeth:
            if tooth.tooth_number == str(tooth_number):
                return tooth
        return None

    def apply_procedure_to_tooth(self, tooth_number: str, surface: str, condition: str):
        """
        Apply a procedure result to the relevant tooth surface.
        Called when a procedure is marked 'Completed'.
        e.g. apply_procedure_to_tooth("14", "MO", "Filling - Composite")
        """
        tooth = self.get_tooth_by_number(tooth_number)
        if not tooth:
            frappe.throw(_(f"Tooth #{tooth_number} not found in this encounter's chart."))
        surfaces = [s.strip().upper() for s in surface.split(",")]
        surface_map = {
            "M": "mesial", "D": "distal", "O": "occlusal_incisal",
            "I": "occlusal_incisal", "B": "buccal_facial",
            "F": "buccal_facial", "L": "lingual_palatal", "P": "lingual_palatal"
        }
        for s in surfaces:
            field = surface_map.get(s)
            if field:
                tooth.set(field, condition)
        # Update overall condition if applicable
        if condition in ("Crown", "Missing", "Extracted", "Implant", "RCT - Root Canal Treated"):
            tooth.overall_condition = condition
        elif "Caries" in condition:
            tooth.overall_condition = "Caries"
        elif "Filling" in condition:
            tooth.overall_condition = "Filled"

    def finalize_odontogram_snapshot(self):
        """Mark the encounter as having a finalized chart state."""
        frappe.db.set_value(
            "Dental Encounter", self.name,
            "encounter_status", "Completed",
            update_modified=False
        )

    # ─────────────────────────────────────────────
    # Billing Integration
    # ─────────────────────────────────────────────

    def create_or_update_sales_invoice(self):
        """
        Auto-create a Sales Invoice when encounter is submitted.
        Only bills procedures with status = 'Completed'.
        Maps CDT codes to ERPNext Items via Procedure Code -> linked_item.
        """
        completed_procedures = [
            p for p in self.procedures
            if p.status == "Completed" and not p.billed_to_invoice
        ]
        if not completed_procedures:
            frappe.msgprint(_("No completed procedures to bill."))
            return

        # Get or create invoice
        if self.sales_invoice:
            invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
        else:
            patient_doc = frappe.get_doc("Patient", self.patient)
            invoice = frappe.new_doc("Sales Invoice")
            invoice.customer = self._get_or_create_customer(patient_doc)
            invoice.posting_date = self.encounter_date or nowdate()
            invoice.due_date = self.encounter_date or nowdate()
            invoice.custom_dental_encounter = self.name
            invoice.items = []

        for proc in completed_procedures:
            proc_code_doc = frappe.get_doc("Procedure Code", proc.procedure_code)
            item_code = proc_code_doc.linked_item
            if not item_code:
                # Auto-create Item if not linked
                item_code = self._ensure_item_exists(proc_code_doc)

            invoice.append("items", {
                "item_code": item_code,
                "item_name": f"[{proc.procedure_code}] {proc.procedure_name}",
                "description": (
                    f"CDT: {proc.procedure_code} | "
                    f"Tooth: {proc.tooth_number or 'N/A'} | "
                    f"Surface: {proc.surface or 'N/A'} | "
                    f"Provider: {proc.provider or self.provider}"
                ),
                "qty": 1,
                "rate": flt(proc.fee),
                "amount": flt(proc.fee),
            })
            proc.billed_to_invoice = 1

        invoice.save()
        self.sales_invoice = invoice.name

        # Update billed flags on the encounter (bypass submit validation)
        for proc in completed_procedures:
            frappe.db.set_value(
                "Encounter Procedure", proc.name,
                {"billed_to_invoice": 1, "invoice_row_ref": invoice.name},
                update_modified=False
            )
        frappe.msgprint(_(f"Sales Invoice {invoice.name} created/updated successfully."))

    def _get_or_create_customer(self, patient_doc):
        """Map Patient to ERPNext Customer, creating one if needed."""
        existing = frappe.db.get_value(
            "Customer", {"customer_name": patient_doc.full_name}, "name"
        )
        if existing:
            return existing
        customer = frappe.new_doc("Customer")
        customer.customer_name = patient_doc.full_name
        customer.customer_type = "Individual"
        customer.customer_group = "Dental Patients"
        customer.territory = "All Territories"
        customer.save(ignore_permissions=True)
        # Link back to patient
        frappe.db.set_value("Patient", patient_doc.name, "linked_user", customer.name)
        return customer.name

    def _ensure_item_exists(self, proc_code_doc):
        """Create an ERPNext Item for a CDT code if none is linked."""
        item_code = f"CDT-{proc_code_doc.cdt_code}"
        if not frappe.db.exists("Item", item_code):
            item = frappe.new_doc("Item")
            item.item_code = item_code
            item.item_name = proc_code_doc.procedure_name
            item.item_group = "Dental Services"
            item.stock_uom = "Nos"
            item.is_stock_item = 0
            item.is_sales_item = 1
            item.description = proc_code_doc.full_description or proc_code_doc.procedure_name
            item.standard_rate = flt(proc_code_doc.standard_fee)
            item.save(ignore_permissions=True)
            # Link back to procedure code
            frappe.db.set_value("Procedure Code", proc_code_doc.name, "linked_item", item_code)
        return item_code

    def cancel_linked_invoice(self):
        if self.sales_invoice:
            inv = frappe.get_doc("Sales Invoice", self.sales_invoice)
            if inv.docstatus == 1:
                inv.cancel()
                frappe.msgprint(_(f"Sales Invoice {self.sales_invoice} has been cancelled."))

    def update_patient_last_visit(self):
        frappe.db.set_value(
            "Patient", self.patient,
            "last_visit_date", self.encounter_date,
            update_modified=False
        )


# ─────────────────────────────────────────────────────────────
# Odontogram Logic Class
# Manages the visual/state representation of a single tooth
# ─────────────────────────────────────────────────────────────

class OdontogramLogic:
    """
    Translates tooth field data into an SVG render-state dictionary.
    This dict is consumed by the React Odontogram component on the frontend.

    Color conventions (standard dental charting):
    - Blue  = Existing restorations (completed)
    - Red   = Caries / pathology / planned treatment
    - Black = Existing amalgam
    - Gold  = Crown / existing gold
    - Gray  = Missing / extracted
    - Green = Healthy / normal
    """

    CONDITION_COLORS = {
        "Healthy":                  "#22c55e",   # green
        "Caries":                   "#ef4444",   # red
        "Filled":                   "#3b82f6",   # blue (composite)
        "Filling - Composite":      "#3b82f6",   # blue
        "Filling - Amalgam":        "#374151",   # dark gray/black
        "Filling - Gold":           "#f59e0b",   # gold
        "Filling - Ceramic":        "#e0e7ff",   # light lavender
        "Crown":                    "#f59e0b",   # gold
        "Missing":                  "#9ca3af",   # gray
        "Extracted":                "#6b7280",   # darker gray
        "Implant":                  "#8b5cf6",   # purple
        "RCT - Root Canal Treated": "#ec4899",   # pink
        "Bridge Abutment":          "#f59e0b",   # gold
        "Bridge Pontic":            "#d1d5db",   # light gray
        "Veneer":                   "#a5f3fc",   # cyan
        "Fracture":                 "#dc2626",   # dark red
        "Watched":                  "#fbbf24",   # yellow/amber
        "Sealant":                  "#bbf7d0",   # light green
        "Open Margin":              "#fca5a5",   # light red
        "Recurrent Decay":          "#b91c1c",   # crimson
    }

    SURFACE_KEYS = ["mesial", "distal", "occlusal_incisal", "buccal_facial", "lingual_palatal"]

    def __init__(self, tooth_row):
        self.tooth = tooth_row

    def compute_svg_state(self) -> dict:
        """
        Returns a dictionary with all info the React SVG component needs to render.
        """
        state = {
            "tooth_number":       self.tooth.tooth_number,
            "overall_condition":  self.tooth.overall_condition or "Healthy",
            "overall_color":      self._color_for(self.tooth.overall_condition or "Healthy"),
            "is_missing":         self.tooth.overall_condition in ("Missing", "Extracted"),
            "is_implant":         self.tooth.overall_condition == "Implant",
            "is_crown":           self.tooth.overall_condition == "Crown",
            "is_rct":             self.tooth.overall_condition == "RCT - Root Canal Treated",
            "mobility":           self.tooth.mobility or "0 - None",
            "furcation":          self.tooth.furcation or "N/A",
            "bleeding":           bool(self.tooth.bleeding_on_probing),
            "recession":          self.tooth.recession_mm or 0,
            "surfaces": {
                "M": self._surface_state("mesial"),
                "D": self._surface_state("distal"),
                "O": self._surface_state("occlusal_incisal"),
                "B": self._surface_state("buccal_facial"),
                "L": self._surface_state("lingual_palatal"),
            },
            "notes":              self.tooth.tooth_notes or "",
            "last_updated_by":    self.tooth.last_updated_by or "",
            "last_updated_on":    str(self.tooth.last_updated_on or ""),
        }
        return state

    def _surface_state(self, field_name: str) -> dict:
        value = getattr(self.tooth, field_name, None) or "Healthy"
        return {
            "condition": value,
            "color": self._color_for(value),
            "is_pathologic": self._is_pathologic(value),
        }

    def _color_for(self, condition: str) -> str:
        return self.CONDITION_COLORS.get(condition, "#22c55e")

    def _is_pathologic(self, condition: str) -> bool:
        pathologic = {"Caries", "Fracture", "Open Margin", "Recurrent Decay", "Watched"}
        return condition in pathologic

    @staticmethod
    def get_full_chart_state(patient: str) -> list:
        """
        Fetch the latest tooth chart state for a patient from the most
        recent completed Dental Encounter. Used by the Odontogram page.
        """
        encounters = frappe.get_list(
            "Dental Encounter",
            filters={"patient": patient, "docstatus": 1},
            fields=["name", "encounter_date"],
            order_by="encounter_date desc",
            limit=1
        )
        if not encounters:
            return OdontogramLogic._default_chart()

        enc = frappe.get_doc("Dental Encounter", encounters[0].name)
        chart = []
        for tooth in enc.teeth:
            logic = OdontogramLogic(tooth)
            chart.append(logic.compute_svg_state())
        return chart

    @staticmethod
    def _default_chart() -> list:
        """Return a blank 32-tooth chart (all healthy) for new patients."""
        teeth = list(range(1, 33))
        default = []
        for t in teeth:
            default.append({
                "tooth_number": str(t),
                "overall_condition": "Healthy",
                "overall_color": "#22c55e",
                "is_missing": False,
                "is_implant": False,
                "is_crown": False,
                "is_rct": False,
                "mobility": "0 - None",
                "furcation": "N/A",
                "bleeding": False,
                "recession": 0,
                "surfaces": {
                    s: {"condition": "Healthy", "color": "#22c55e", "is_pathologic": False}
                    for s in ["M", "D", "O", "B", "L"]
                },
                "notes": "",
                "last_updated_by": "",
                "last_updated_on": "",
            })
        return default
