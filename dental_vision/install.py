"""
install.py — DentalVision Pro v2.0.8
Idempotent post-install setup — safe to run multiple times.
Checks all parent dependencies before inserting records.
"""
import frappe
from frappe import _


def after_install():
    print("🦷 DentalVision Pro v2.0.8 — Running post-install setup...")
    _create_roles()
    _create_item_group()
    _create_customer_group()
    _create_image_categories()
    _create_operatories()
    print("✅ DentalVision Pro installed successfully.")
    print("ℹ️  To load CDT codes: dental_vision.install.seed_cdt_codes()")


def after_migrate():
    """Called on every bench migrate — safe to run repeatedly."""
    _create_roles()
    _create_item_group()
    _create_customer_group()
    _create_image_categories()


def _create_roles():
    roles = [
        ("Dentist",               "Full clinical access"),
        ("Dental Hygienist",      "Clinical access — perio, hygiene procedures"),
        ("Dental Receptionist",   "Scheduling and patient registration"),
        ("Dental Billing",        "Insurance claims and payment entry"),
        ("Dental Office Manager", "Full access including reports and settings"),
    ]
    for role_name, desc in roles:
        if not frappe.db.exists("Role", role_name):
            try:
                frappe.get_doc({
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                    "description": desc,
                }).insert(ignore_permissions=True)
                print(f"  ✓ Created role: {role_name}")
            except Exception as e:
                frappe.log_error(f"Role creation error {role_name}: {e}")


def _create_item_group():
    # Check parent exists before inserting child
    if not frappe.db.exists("Item Group", "All Item Groups"):
        print("  ⏭ Skipping Item Groups: parent 'All Item Groups' not found")
        return
    if not frappe.db.exists("Item Group", "Dental Services"):
        try:
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": "Dental Services",
                "parent_item_group": "All Item Groups",
                "is_group": 0,
            }).insert(ignore_permissions=True)
            print("  ✓ Created Item Group: Dental Services")
        except Exception as e:
            frappe.log_error(f"Item Group error: {e}")


def _create_customer_group():
    # Per Gemini brief: check for parent dependency first
    if not frappe.db.exists("Customer Group", "All Customer Groups"):
        print("  ⏭ Skipping Customer Group: 'All Customer Groups' root not found (ERPNext setup incomplete)")
        return
    if not frappe.db.exists("Customer Group", "Dental Patients"):
        try:
            frappe.get_doc({
                "doctype": "Customer Group",
                "customer_group_name": "Dental Patients",
                "parent_customer_group": "All Customer Groups",
                "is_group": 0,
            }).insert(ignore_permissions=True)
            print("  ✓ Created Customer Group: Dental Patients")
        except Exception as e:
            frappe.log_error(f"Customer Group error: {e}")


def _create_image_categories():
    if not frappe.db.exists("DocType", "Dental Image Category"):
        print("  ⏭ Skipping Image Categories: DocType not yet synced")
        return
    categories = [
        ("X-ray PA (Periapical)",     "Radiograph"),
        ("X-ray Bitewing",            "Radiograph"),
        ("X-ray Panoramic (OPG)",     "Radiograph"),
        ("X-ray CBCT 3D",             "Radiograph"),
        ("Photograph — Intraoral",    "Photograph"),
        ("Photograph — Extraoral",    "Photograph"),
        ("Consent Form",              "Consent Form"),
        ("Medical History Form",      "Consent Form"),
        ("Lab Result",                "Lab Result"),
        ("Referral Letter",           "Referral Letter"),
        ("Insurance Card",            "Other"),
        ("Other",                     "Other"),
    ]
    inserted = 0
    for cat_name, cat_type in categories:
        if not frappe.db.exists("Dental Image Category", cat_name):
            try:
                frappe.get_doc({
                    "doctype": "Dental Image Category",
                    "category_name": cat_name,
                    "category_type": cat_type,
                    "is_active": 1,
                }).insert(ignore_permissions=True)
                inserted += 1
            except Exception as e:
                frappe.log_error(f"Image category error {cat_name}: {e}")
    if inserted:
        print(f"  ✓ Created {inserted} image categories")


def _create_operatories():
    if not frappe.db.exists("DocType", "Dental Operatory"):
        print("  ⏭ Skipping Operatories: DocType not yet synced")
        return
    operatories = [
        ("Op 1 — General", "OP1", 0),
        ("Op 2 — General", "OP2", 0),
        ("Op 3 — Hygiene", "OP3", 1),
    ]
    for name, abbr, is_hygiene in operatories:
        if not frappe.db.exists("Dental Operatory", name):
            try:
                frappe.get_doc({
                    "doctype": "Dental Operatory",
                    "operatory_name": name,
                    "operatory_abbr": abbr,
                    "is_hygiene": is_hygiene,
                    "is_active": 1,
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Operatory error {name}: {e}")
    print("  ✓ Operatories created (if DocType was available)")


@frappe.whitelist()
def seed_cdt_codes():
    """Run from System Console after install: dental_vision.install.seed_cdt_codes()"""
    if not frappe.db.exists("DocType", "Procedure Code"):
        return {"error": "Procedure Code DocType not found. Run bench migrate first."}

    cdt_codes = [
        # Diagnostic
        ("D0120","Periodic oral evaluation","Diagnostic",65.0,False,"D0120"),
        ("D0140","Limited oral evaluation","Diagnostic",85.0,False,"D0140"),
        ("D0150","Comprehensive oral evaluation - new patient","Diagnostic",110.0,False,"D0150"),
        ("D0180","Comprehensive periodontal evaluation","Diagnostic",130.0,False,"D0180"),
        ("D0210","Intraoral - complete series","Diagnostic",180.0,False,"FMX"),
        ("D0220","Intraoral - periapical first image","Diagnostic",35.0,True,"PA x1"),
        ("D0230","Intraoral - periapical each additional","Diagnostic",25.0,True,"PA add"),
        ("D0272","Bitewings - two images","Diagnostic",50.0,False,"BW x2"),
        ("D0274","Bitewings - four images","Diagnostic",90.0,False,"BW x4"),
        ("D0330","Panoramic radiographic image","Diagnostic",175.0,False,"PAN"),
        ("D0340","2D cephalometric radiographic image","Diagnostic",160.0,False,"Ceph"),
        ("D0364","Cone beam CT - limited field","Diagnostic",450.0,False,"CBCT Ltd"),
        # Preventive
        ("D1110","Prophylaxis - adult","Preventive",110.0,False,"Prophy-Adult"),
        ("D1120","Prophylaxis - child","Preventive",80.0,False,"Prophy-Child"),
        ("D1206","Topical fluoride varnish","Preventive",40.0,False,"Fluoride Varnish"),
        ("D1330","Oral hygiene instructions","Preventive",40.0,False,"OHI"),
        ("D1351","Sealant - per tooth","Preventive",55.0,True,"Sealant"),
        # Restorative
        ("D2140","Amalgam - one surface","Restorative",185.0,True,"Amalgam 1S"),
        ("D2150","Amalgam - two surfaces","Restorative",225.0,True,"Amalgam 2S"),
        ("D2160","Amalgam - three surfaces","Restorative",265.0,True,"Amalgam 3S"),
        ("D2330","Composite - one surface, anterior","Restorative",195.0,True,"Comp Ant 1S"),
        ("D2331","Composite - two surfaces, anterior","Restorative",245.0,True,"Comp Ant 2S"),
        ("D2391","Composite - one surface, posterior","Restorative",215.0,True,"Comp Post 1S"),
        ("D2392","Composite - two surfaces, posterior","Restorative",265.0,True,"Comp Post 2S"),
        ("D2393","Composite - three surfaces, posterior","Restorative",315.0,True,"Comp Post 3S"),
        ("D2740","Crown - porcelain/ceramic","Restorative",1350.0,True,"Crown Ceramic"),
        ("D2750","Crown - porcelain fused to metal","Restorative",1250.0,True,"Crown PFM"),
        ("D2950","Core build-up","Restorative",250.0,True,"Core Build-up"),
        ("D2930","Prefabricated stainless steel crown - primary","Restorative",285.0,True,"SSC Primary"),
        ("D2940","Protective restoration","Restorative",120.0,True,"IRM/GIC"),
        # Endodontics
        ("D3110","Pulp cap - direct","Endodontics",120.0,True,"Direct Pulp Cap"),
        ("D3220","Therapeutic pulpotomy","Endodontics",250.0,True,"Pulpotomy"),
        ("D3310","Endodontic therapy, anterior","Endodontics",850.0,True,"RCT Anterior"),
        ("D3320","Endodontic therapy, premolar","Endodontics",950.0,True,"RCT Premolar"),
        ("D3330","Endodontic therapy, molar","Endodontics",1150.0,True,"RCT Molar"),
        # Periodontics
        ("D4341","Scaling and root planing - 4+ teeth per Q","Periodontics",310.0,False,"SRP 4+/Q"),
        ("D4342","Scaling and root planing - 1-3 teeth per Q","Periodontics",230.0,False,"SRP 1-3/Q"),
        ("D4355","Full mouth debridement","Periodontics",175.0,False,"FMD"),
        ("D4910","Periodontal maintenance","Periodontics",175.0,False,"Perio Maint"),
        # Oral Surgery
        ("D7140","Extraction, erupted tooth","Oral Surgery",185.0,True,"Extraction"),
        ("D7210","Extraction, surgical","Oral Surgery",325.0,True,"Surgical Ext"),
        ("D7220","Impacted tooth - soft tissue","Oral Surgery",450.0,True,"Impacted Soft"),
        ("D7230","Impacted tooth - partially bony","Oral Surgery",550.0,True,"Impacted Partial"),
        ("D7240","Impacted tooth - fully bony","Oral Surgery",650.0,True,"Impacted Full"),
        ("D7510","Incision and drainage - intraoral","Oral Surgery",250.0,False,"I&D"),
        # Adjunctive
        ("D9110","Palliative treatment of dental pain","Adjunctive",95.0,False,"Palliative"),
        ("D9210","Local anesthesia","Adjunctive",55.0,True,"Local Anesthesia"),
        ("D9310","Consultation","Adjunctive",150.0,False,"Consultation"),
        ("D9930","Treatment of complications - postoperative","Adjunctive",95.0,False,"Post-Op"),
        ("D9940","Occlusal guard","Adjunctive",550.0,False,"Night Guard"),
        ("D9951","Occlusal adjustment - limited","Adjunctive",130.0,False,"Occlusal Adj"),
        ("D9986","Missed appointment","Adjunctive",50.0,False,"Missed Appt"),
        ("D9987","Cancelled appointment","Adjunctive",50.0,False,"Cancelled Appt"),
    ]

    inserted = 0
    for code, name, category, fee, requires_tooth, abbrev in cdt_codes:
        if not frappe.db.exists("Procedure Code", code):
            try:
                frappe.get_doc({
                    "doctype": "Procedure Code",
                    "cdt_code": code,
                    "procedure_name": name,
                    "category": category,
                    "standard_fee": fee,
                    "abbreviation": abbrev,
                    "requires_tooth_number": 1 if requires_tooth else 0,
                    "is_active": 1,
                }).insert(ignore_permissions=True)
                inserted += 1
            except Exception as e:
                frappe.log_error(f"CDT seed error {code}: {e}")

    frappe.db.commit()
    msg = f"✓ Seeded {inserted} CDT codes ({len(cdt_codes)} in library)"
    print(msg)
    return {"inserted": inserted, "total": len(cdt_codes)}
