"""Read-only B08 retention comparison; strip only documented new schema columns."""
import hashlib
import json
import os

import frappe

os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
try:
    assert frappe.conf.get("allow_tests")
    assert not frappe.db.exists("Workflow", {"document_type": "Work Order"})
    excluded = {
        "Work Order": ["workflow_state", "production_team", "approval_requested_by", "approval_reviewed_by", "approval_note", "previous_work_order"],
        "Work Order Operation": ["report_scope", "report_department", "report_employee", "report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency"],
        "Job Card": ["report_request_id", "report_payload_hash", "report_shutdown_seconds", "report_overtime_seconds", "report_effective_seconds", "report_time_rule", "report_time_context", "correction_reason", "report_metrics_context", "report_estimated_wage"],
    }
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment"]
    result = {}
    for dt in tables:
        rows = frappe.get_all(dt, fields=["*"], order_by="name")
        for row in rows:
            for field in excluded.get(dt, []):
                row.pop(field, None)
        result[dt] = dict(count=len(rows), sha256=hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest())
    print(json.dumps(dict(business_data=result, workflow_count=0, excluded_columns=excluded), indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
