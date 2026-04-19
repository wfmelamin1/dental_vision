"""
hayat_dental_home.py
Context provider for the Hayat Dental Vision homepage.
Frappe requires this companion .py file for www templates.
"""

no_cache = 1

def get_context(context):
    context.title = "Hayat Specialist Hospital — Dental Vision Center"
    context.description = "Advanced dental care in Kano. Book your appointment online."
    context.no_breadcrumbs = 1
    context.show_sidebar = 0
    return context
