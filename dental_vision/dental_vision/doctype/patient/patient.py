"""
patient.py - Frappe controller for the Patient DocType
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, nowdate, add_months


class Patient(Document):

    def before_insert(self):
        self.patient_id = self._generate_patient_id()

    def validate(self):
        self.full_name = f"{self.first_name} {self.last_name}".strip()
        self.age = self._calculate_age()
        self._validate_dob()
        self._set_recall_date()

    def after_insert(self):
        self._create_default_tooth_chart()

    def _generate_patient_id(self):
        """Generate a sequential patient ID: PAT-00001"""
        last = frappe.db.sql(
            "SELECT patient_id FROM `tabPatient` ORDER BY creation DESC LIMIT 1"
        )
        if last and last[0][0]:
            try:
                num = int(last[0][0].split("-")[1]) + 1
            except Exception:
                num = 1
        else:
            num = 1
        return f"PAT-{str(num).zfill(5)}"

    def _calculate_age(self):
        if self.date_of_birth:
            return int(date_diff(nowdate(), self.date_of_birth) / 365.25)
        return 0

    def _validate_dob(self):
        if self.date_of_birth and getdate(self.date_of_birth) > getdate(nowdate()):
            frappe.throw(_("Date of Birth cannot be in the future."))

    def _set_recall_date(self):
        if self.last_visit_date and self.recall_interval:
            self.next_recall_date = add_months(self.last_visit_date, self.recall_interval)

    def _create_default_tooth_chart(self):
        """
        When a new patient is created, pre-populate a default Dental Encounter
        with all 32 adult teeth in Healthy state. This gives the dentist a
        blank chart ready for the first exam.
        """
        pass  # Implemented as a server script to keep it no-code friendly
