"""Patient setup hooks."""
import frappe

def create_initial_chart(doc, method=None):
    """Called after a new Patient is inserted. No-op for MVP."""
    pass
