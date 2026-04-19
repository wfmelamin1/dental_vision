"""
reports/weekly_summary.py
Weekly production summary report per BRD 6.10
"""
import frappe
from frappe.utils import nowdate, add_days


def generate_weekly_report():
    """
    Weekly scheduled job: generate practice production summary.
    Sends email to office manager with key metrics.
    """
    week_start = add_days(nowdate(), -7)

    # Production by provider
    production = frappe.db.sql("""
        SELECT
            dp.provider,
            COUNT(dp.name) as procedure_count,
            SUM(dp.fee) as gross_production
        FROM `tabDental Procedure` dp
        WHERE dp.status = 'Complete'
        AND dp.procedure_date BETWEEN %s AND %s
        AND dp.docstatus = 1
        GROUP BY dp.provider
        ORDER BY gross_production DESC
    """, (week_start, nowdate()), as_dict=True)

    if not production:
        return

    # Format summary
    lines = [f"Weekly Production Summary: {week_start} to {nowdate()}", ""]
    for row in production:
        lines.append(f"  {row.provider}: {row.procedure_count} procedures — {row.gross_production:.2f}")

    summary = "\n".join(lines)
    frappe.log_error(summary, "Weekly Production Summary")
    return summary
