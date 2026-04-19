"""
hooks.py — DentalVision Pro
Frappe App Hooks — aligned with Elrazi University Clinic BRD v1.0
"""

app_name = "dental_vision"
app_title = "DentalVision Pro"
app_publisher = "Elrazi University Clinic"
app_description = "Dental Practice Management System based on OpenDental, built on Frappe/ERPNext"
app_email = "admin@elrazi.edu"
app_license = "MIT"
app_version = "2.1.1"

# ─────────────────────────────────────────────
# App Assets (minimal — no JS bundle needed)
# ─────────────────────────────────────────────
app_include_css = []
app_include_js = []

# ─────────────────────────────────────────────
# DocType JavaScript enhancements
# ─────────────────────────────────────────────
doctype_js = {}
doctype_list_js = {}

# ─────────────────────────────────────────────
# Document Events
# ─────────────────────────────────────────────
doc_events = {
    "Dental Encounter": {
        "on_submit": [
            "dental_vision.billing.auto_billing.create_invoice_on_encounter_submit",
        ],
        "on_cancel": [
            "dental_vision.billing.auto_billing.cancel_invoice_on_encounter_cancel",
        ],
        "validate": [
            "dental_vision.clinical.odontogram.validate_tooth_chart",
        ],
    },
    "Sales Invoice": {
        "on_submit": [
            "dental_vision.billing.insurance.submit_insurance_claim",
        ],
    },
    "Patient": {
        "after_insert": [
            "dental_vision.clinical.patient_setup.create_initial_chart",
        ],
    },
    "Patient Appointment": {
        "on_update": [
            "dental_vision.scheduling.reminders.handle_status_change",
        ],
    },
    "Dental Procedure": {
        "on_submit": [
            "dental_vision.clinical.procedures.on_procedure_complete",
        ],
    },
    "Dental Treatment Plan": {
        "validate": [
            "dental_vision.clinical.treatment_plan.enforce_single_active_plan",
        ],
    },
}

# ─────────────────────────────────────────────
# Scheduled Tasks
# ─────────────────────────────────────────────
scheduler_events = {
    "daily": [
        "dental_vision.scheduling.recalls.send_recall_reminders",
        "dental_vision.scheduling.reminders.send_appointment_reminders",
    ],
    "weekly": [
        "dental_vision.reports.weekly_summary.generate_weekly_report",
    ],
    "monthly": [
        "dental_vision.billing.insurance.follow_up_unpaid_claims",
        "dental_vision.billing.statements.generate_patient_statements",
    ],
}

# ─────────────────────────────────────────────
# Fixtures — export with app for fresh deployments
# ─────────────────────────────────────────────
fixtures = [
    {
        "doctype": "Role",
        "filters": [["name", "in", [
            "Dentist",
            "Dental Hygienist",
            "Dental Receptionist",
            "Dental Billing",
            "Dental Office Manager",
        ]]]
    },
    {"doctype": "Procedure Code"},
    {"doctype": "Dental Image Category"},
]

# ─────────────────────────────────────────────
# Installation Hooks
# ─────────────────────────────────────────────
after_install = "dental_vision.install.after_install"
after_migrate = "dental_vision.install.after_migrate"

# ─────────────────────────────────────────────
# HIPAA / GDPR — User Data Fields
# ─────────────────────────────────────────────
user_data_fields = [
    {
        "doctype": "Patient",
        "filter_by": "email",
        "redact_fields": [
            "email", "mobile_phone", "home_phone",
            "allergies", "medical_history_notes"
        ],
        "partial": 1,
    },
    {
        "doctype": "Dental Encounter",
        "filter_by": "patient",
        "strict": 0,
    },
    {
        "doctype": "Dental Perio Exam",
        "filter_by": "patient",
        "strict": 0,
    },
]

# ─────────────────────────────────────────────
# Website Routes
# ─────────────────────────────────────────────
website_route_rules = [
    # Public homepage — served at hayat.frappe.cloud/hayat-dental
    {"from_route": "/hayat-dental", "to_route": "hayat_dental_home"},
    # Patient portal
    {"from_route": "/patient-portal/<path:name>", "to_route": "patient-portal"},
]

# ─────────────────────────────────────────────
# Website Assets (injected into all pages)
# ─────────────────────────────────────────────
website_theme_no_sidebar = 1
