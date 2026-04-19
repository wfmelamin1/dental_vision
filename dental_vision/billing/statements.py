"""
billing/statements.py
Monthly patient statement generation per BRD 6.8
"""
import frappe
from frappe.utils import nowdate, add_months


def generate_patient_statements():
    """
    Monthly scheduled job: generate and email statements
    for patients with outstanding balances > 0.
    """
    patients_with_balance = frappe.db.sql("""
        SELECT DISTINCT si.customer, p.full_name, p.email
        FROM `tabSales Invoice` si
        JOIN `tabPatient` p ON p.name = si.patient
        WHERE si.outstanding_amount > 0
        AND si.docstatus = 1
        AND p.email IS NOT NULL
        AND p.email != ''
    """, as_dict=True)

    sent = 0
    for row in patients_with_balance:
        try:
            frappe.sendmail(
                recipients=[row.email],
                subject=f"Your Dental Account Statement — {nowdate()}",
                message=f"""
Dear {row.full_name},

This is your monthly account statement from Elrazi University Dental Clinic.

You have an outstanding balance on your account.
Please contact our billing department or log into the patient portal
to view your full statement and make a payment.

Thank you,
Elrazi University Dental Clinic Billing Team
                """.strip()
            )
            sent += 1
        except Exception as e:
            frappe.log_error(f"Statement email failed for {row.email}: {e}")

    return f"Statements sent: {sent}"
