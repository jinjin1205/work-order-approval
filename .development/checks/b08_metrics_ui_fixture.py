"""Prepare three new B08 synthetic orders; never replay or modify old acceptance samples.

Run only after the maintained pricing metadata has been installed on the retained
B08-only site. This script prepares orders; it does not preview or confirm reports.
The baseline stores each table's current columns and a hash per existing row.
Later preservation checks must select only those captured columns, keyed by name.
"""
import hashlib
import json
import os
from pathlib import Path

import frappe
from frappe.permissions import add_user_permission
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval


os.umask(0o077)
os.chdir("sites")
private = Path("/tmp/b08-private")
source = json.loads((private / "fixture.json").read_text())
target = private / "metrics-20261028.json"
baseline_path = private / "metrics-20261028-before.json"
assert not target.exists(), "Existing metrics fixture must be inspected, not recreated"
assert not baseline_path.exists(), "Preserve the existing baseline; do not recapture it"
assert source["site"] == "xgd-b08-http.localhost"

frappe.init(site=source["site"])
frappe.connect()
try:
    assert frappe.conf.b08_http_only, "Only the dedicated synthetic B08 site is allowed"
    frappe.set_user("Administrator")
    tables = [
        "Work Order", "Work Order Item", "Work Order Operation", "Job Card",
        "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry",
        "Workflow Action", "Version", "Comment",
    ]
    baseline = {
        "site": source["site"],
        "captured_at": str(frappe.utils.now_datetime()),
        "hash_algorithm": "sha256(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str, separators=(',', ':')).encode('utf-8'))",
        "comparison_scope": "Every captured row and column must remain identical; additional rows/columns are compared separately.",
        "tables": {},
    }
    for doctype in tables:
        columns = sorted(frappe.db.get_table_columns(doctype))
        rows = frappe.get_all(doctype, fields=columns, order_by="name", limit_page_length=0)
        baseline["tables"][doctype] = {
            "columns": columns,
            "count": len(rows),
            "rows": {
                row.name: hashlib.sha256(json.dumps(
                    dict(row), sort_keys=True, ensure_ascii=False, default=str,
                    separators=(",", ":"),
                ).encode("utf-8")).hexdigest()
                for row in rows
            },
        }
    with baseline_path.open("x", encoding="utf-8") as output:
        json.dump(baseline, output, ensure_ascii=False, indent=2)
        output.write("\n")

    original = frappe.get_doc("Work Order", source["order"])
    assert original.qty == 10 and len(original.operations) == 3
    employee = frappe.get_doc("Employee", source["employee"])
    assert employee.user_id == source["user"] and employee.status == "Active"
    assert employee.company == original.company
    assert "生产报工" in frappe.get_roles(source["user"])
    director = source["user"].replace("-report@", "-director@")
    assert director != source["user"] and "生产工单签批" in frappe.get_roles(director)
    actors = [original.approval_requested_by, original.approval_reviewed_by, director]
    assert all(actors), "Original native approval actors must be available"
    assert not any(original.get(field) for field in (
        "sales_order", "sales_order_item", "material_request", "material_request_item",
        "production_plan", "production_plan_item", "production_plan_sub_assembly_item",
    )), "This fixture must not carry external production or sales references"

    expected_fields = ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency")
    assert all(frappe.get_meta("Work Order Operation").has_field(field) for field in expected_fields)
    values = {"site": source["site"], "user": source["user"], "orders": {}}
    for key, mode in (("hourly", "hourly"), ("piece", "piece"), ("draft", None)):
        frappe.set_user(actors[0])
        order = frappe.copy_doc(original)
        order.docstatus = 0
        order.status = "Draft"
        order.workflow_state = "草稿"
        for field in ("approval_requested_by", "approval_reviewed_by", "approval_note", "amended_from", "previous_work_order",
                      "actual_start_date", "actual_end_date"):
            order.set(field, None)
        for field in ("produced_qty", "material_transferred_for_manufacturing", "process_loss_qty",
                      "actual_operating_cost", "corrective_operation_cost", "lead_time"):
            order.set(field, 0)
        for row in order.operations:
            row.docstatus = 0
            row.status = "Pending"
            for field in ("completed_qty", "process_loss_qty", "actual_operation_time", "actual_operating_cost"):
                row.set(field, 0)
            row.actual_start_time = row.actual_end_time = None
            for field in expected_fields:
                row.set(field, None)
        for row in order.required_items:
            row.docstatus = 0
            for field in ("transferred_qty", "consumed_qty", "returned_qty"):
                row.set(field, 0)
        operation = order.operations[0]
        operation.report_scope = "PERSON"
        operation.report_employee = source["employee"]
        operation.report_department = None
        if mode:
            operation.report_wage_mode = mode
            operation.report_wage_rate = "10"
            operation.report_standard_efficiency = "10"
        order.insert()
        if mode:
            for actor, action in zip(actors, ("送审", "审核通过", "签批通过")):
                frappe.set_user(actor)
                apply_production_approval(order.name, action, str(order.modified))
                order.reload()
            assert order.docstatus == 1 and order.workflow_state == "已批准"
            assert order.operations[0].report_wage_mode == mode
            assert order.operations[0].report_wage_rate == "10"
            assert order.operations[0].report_standard_efficiency == "10"
            assert order.operations[0].report_wage_currency
        else:
            assert order.docstatus == 0 and order.workflow_state == "草稿"
            assert not any(order.operations[0].get(field) for field in expected_fields)
        assert order.qty == 10 and not order.produced_qty and not order.material_transferred_for_manufacturing
        assert all(not row.completed_qty and not row.process_loss_qty for row in order.operations)
        frappe.set_user("Administrator")
        if mode:
            add_user_permission("Work Order", order.name, source["user"])
        values["orders"][key] = {"order": order.name, "operation_id": order.operations[0].name}

    # Separate synthetic dates keep the two reports from overlapping for the same
    # employee/workstation. Actual submissions remain the browser operator's action.
    values["sample_inputs"] = {
        "hourly": {"from_time": "2026-10-29 09:00:00", "to_time": "2026-10-29 11:00:00",
                   "good_quantity": "8", "bad_quantity": "2", "shutdown_seconds": 0, "overtime_seconds": 0},
        "piece": {"from_time": "2026-10-30 09:00:00", "to_time": "2026-10-30 11:00:00",
                  "good_quantity": "8", "bad_quantity": "2", "shutdown_seconds": 0, "overtime_seconds": 0},
    }
    values["baseline_file"] = str(baseline_path)
    with target.open("x", encoding="utf-8") as output:
        json.dump(values, output, ensure_ascii=False, indent=2)
        output.write("\n")
    frappe.db.commit()
    print(json.dumps({"new_synthetic_orders": 3, "approved_orders": 2, "draft_orders": 1,
                      "baseline_tables": 11, "reports_created": 0, "secrets_exported": False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
