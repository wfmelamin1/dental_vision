"""
api/odontogram.py
REST API endpoints for the Odontogram React component.
These are whitelisted and callable from JavaScript via frappe.call().
"""

import frappe
from frappe import _
from frappe.utils import now_datetime as nowdatetime
import json


@frappe.whitelist()
def get_chart_state(patient: str, encounter: str = ""):
    """
    Return the current tooth chart state for a patient.
    If a specific encounter is given, load from that encounter's teeth table.
    Otherwise, load from the most recent completed encounter.
    Priority: specific encounter > latest encounter > blank default chart.
    """
    frappe.has_permission("Patient", "read", patient, throw=True)

    if encounter:
        enc = frappe.get_doc("Dental Encounter", encounter)
        if enc.patient != patient:
            frappe.throw(_("Encounter does not belong to this patient."))
        teeth = enc.teeth
    else:
        # Get latest encounter
        encounters = frappe.get_list(
            "Dental Encounter",
            filters={"patient": patient, "docstatus": ["!=", 2]},  # not cancelled
            fields=["name"],
            order_by="encounter_date desc, creation desc",
            limit=1
        )
        if not encounters:
            return _build_default_chart()
        enc = frappe.get_doc("Dental Encounter", encounters[0].name)
        teeth = enc.teeth

    if not teeth:
        return _build_default_chart()

    chart_list = []
    for tooth in teeth:
        svg_state = {}
        if tooth.svg_state_json:
            try:
                svg_state = json.loads(tooth.svg_state_json)
            except Exception:
                pass

        chart_list.append({
            "tooth_number":      tooth.tooth_number,
            "overall_condition": tooth.overall_condition or "Healthy",
            "is_missing":        tooth.overall_condition in ("Missing", "Extracted"),
            "is_implant":        tooth.overall_condition == "Implant",
            "is_crown":          tooth.overall_condition == "Crown",
            "is_rct":            tooth.overall_condition == "RCT - Root Canal Treated",
            "surfaces": {
                "M": tooth.mesial or "Healthy",
                "D": tooth.distal or "Healthy",
                "O": tooth.occlusal_incisal or "Healthy",
                "B": tooth.buccal_facial or "Healthy",
                "L": tooth.lingual_palatal or "Healthy",
            },
            "mobility":          tooth.mobility or "0 - None",
            "notes":             tooth.tooth_notes or "",
            "last_updated_by":   tooth.last_updated_by or "",
            "last_updated_on":   str(tooth.last_updated_on or ""),
        })
    return chart_list


@frappe.whitelist()
def save_chart_state(encounter: str, chart_json: str):
    """
    Save the complete chart state from the React component back to the
    Dental Encounter's teeth child table.
    """
    enc = frappe.get_doc("Dental Encounter", encounter)
    frappe.has_permission("Dental Encounter", "write", enc, throw=True)

    if enc.docstatus == 1:
        frappe.throw(_("Cannot modify a submitted encounter. Create an amendment first."))

    chart = json.loads(chart_json)
    surface_map = {
        "M": "mesial", "D": "distal", "O": "occlusal_incisal",
        "B": "buccal_facial", "L": "lingual_palatal"
    }

    # Build a lookup of existing tooth rows
    existing_teeth = {t.tooth_number: t for t in enc.teeth}

    for tooth_num_str, tooth_data in chart.items():
        if tooth_num_str in existing_teeth:
            tooth_row = existing_teeth[tooth_num_str]
        else:
            tooth_row = enc.append("teeth", {"tooth_number": tooth_num_str})

        tooth_row.overall_condition = tooth_data.get("overall_condition", "Healthy")
        tooth_row.tooth_notes = tooth_data.get("notes", "")
        tooth_row.last_updated_by = frappe.session.user
        tooth_row.last_updated_on = nowdatetime()

        surfaces = tooth_data.get("surfaces", {})
        for svg_key, field_name in surface_map.items():
            setattr(tooth_row, field_name, surfaces.get(svg_key, "Healthy"))

        # Recompute SVG state JSON
        from dental_vision.doctype.dental_encounter.dental_encounter import OdontogramLogic
        logic = OdontogramLogic(tooth_row)
        tooth_row.svg_state_json = json.dumps(logic.compute_svg_state())

    enc.save(ignore_permissions=False)
    return {"status": "ok", "encounter": encounter}


@frappe.whitelist()
def apply_condition_to_multiple(encounter: str, tooth_numbers: str, condition: str, surfaces: str = ""):
    """
    Bulk-apply a condition to multiple teeth at once.
    Useful for e.g. marking all upper teeth as having sealants.
    tooth_numbers: comma-separated string e.g. "1,2,3,14"
    surfaces: comma-separated surface keys e.g. "O,B" or "" for overall
    """
    enc = frappe.get_doc("Dental Encounter", encounter)
    frappe.has_permission("Dental Encounter", "write", enc, throw=True)

    teeth_list = [t.strip() for t in tooth_numbers.split(",")]
    surface_list = [s.strip() for s in surfaces.split(",")] if surfaces else []

    surface_map = {
        "M": "mesial", "D": "distal", "O": "occlusal_incisal",
        "B": "buccal_facial", "L": "lingual_palatal"
    }

    existing = {t.tooth_number: t for t in enc.teeth}
    for tn in teeth_list:
        if tn in existing:
            row = existing[tn]
        else:
            row = enc.append("teeth", {"tooth_number": tn})

        if surface_list:
            for s in surface_list:
                field = surface_map.get(s)
                if field:
                    setattr(row, field, condition)
        else:
            row.overall_condition = condition

        row.last_updated_by = frappe.session.user
        row.last_updated_on = nowdatetime()

    enc.save(ignore_permissions=False)
    return {"status": "ok", "updated": teeth_list}


# ─────────────────────────────────────────────
# Helper: Build blank 32-tooth chart
# ─────────────────────────────────────────────

def _build_default_chart():
    teeth = list(range(1, 33))
    return [
        {
            "tooth_number":      str(t),
            "overall_condition": "Healthy",
            "is_missing":        False,
            "is_implant":        False,
            "is_crown":          False,
            "is_rct":            False,
            "surfaces":          {"M": "Healthy", "D": "Healthy", "O": "Healthy", "B": "Healthy", "L": "Healthy"},
            "mobility":          "0 - None",
            "notes":             "",
            "last_updated_by":   "",
            "last_updated_on":   "",
        }
        for t in teeth
    ]
