"""I05-only fixture and fresh-connection DB observations. Setup is never replayed.

Reuse the existing table/snapshot helpers without changing their PRIVATE globals.
No initial report is created: the sole report belongs to the later HTTP request.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import erpnext
import frappe
from b08_distinct_concurrency_fixture import (
    BUSINESS, SECURITY, EXTRA, STOCK, capture_tables, compare_tables, preserved,
    case_state, digest, write_private,
)

PRIVATE = Path("/tmp/b08-recovery-private")
MANIFEST = Path("/b01/b08-recovery-source-manifest.json")
SCRIPTS = ("b08_recovery_fixture.py", "b08_response_loss_http.py",
           "b08_distinct_concurrency_fixture.py", "b08_distinct_concurrency_http.py")


def source_state():
    manifest = json.loads(MANIFEST.read_text())
    root = Path(erpnext.__file__).resolve().parent.parent
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in manifest["files"]}
    assert len(actual) == 33 and actual == manifest["files"], "Runtime source differs from the approved manifest"
    app = Path(frappe.__file__).resolve().parent / "app.py"
    return {"manifest": manifest, "runtime_files": actual, "runtime_files_match": True,
            "manifest_file_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "frappe_app_sha256": hashlib.sha256(app.read_bytes()).hexdigest(),
            "frappe_version": frappe.__version__, "erpnext_version": erpnext.__version__,
            "scripts": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest() for name in SCRIPTS}}


def setup(runtime):
    from frappe.core.doctype.user.user import generate_keys
    from frappe.permissions import add_user_permission
    from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval

    assert not (PRIVATE / "setup-source.json").exists(), "Never recreate a started fixture"
    write_private(PRIVATE / "setup-source.json", runtime)
    baseline = {"business": capture_tables(BUSINESS), "security": capture_tables(SECURITY), "extra": capture_tables(EXTRA)}
    write_private(PRIVATE / "baseline.json", baseline)
    template = json.loads(Path("/tmp/b08-private/fixture.json").read_text())
    original = frappe.get_doc("Work Order", template["order"])
    assert template["site"] == "xgd-b08-http.localhost" and original.qty == 10 and len(original.operations) == 3
    assert not any(original.get(field) for field in ("sales_order", "sales_order_item", "material_request",
        "material_request_item", "production_plan", "production_plan_item", "production_plan_sub_assembly_item"))
    approval_actors = [original.approval_requested_by, original.approval_reviewed_by,
                       template["user"].replace("-report@", "-director@")]
    for actor, role in zip(approval_actors, ("生产工单发起", "生产工单审核", "生产工单签批")):
        assert role in frappe.get_roles(actor)
    prefix = "b08-recovery-" + frappe.generate_hash(length=10)
    user = prefix + "@example.invalid"
    frappe.get_doc({"doctype": "User", "email": user, "first_name": "响应恢复验收", "language": "zh",
        "enabled": 1, "send_welcome_email": 0, "user_type": "System User", "roles": [{"role": "生产报工"}]}).insert()
    employee = frappe.get_doc({"doctype": "Employee", "first_name": "响应恢复验收", "gender": "Male",
        "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01", "company": original.company,
        "department": original.production_team, "status": "Active", "user_id": user, "create_user_permission": 0}).insert()
    add_user_permission("Company", original.company, user)
    add_user_permission("Department", original.production_team, user, applicable_for="Work Order")
    keys = generate_keys(user)
    assert "System Manager" not in frappe.get_roles(user)
    assert frappe.db.count("Employee", {"user_id": user, "status": "Active"}) == 1
    workstation = frappe.copy_doc(frappe.get_doc("Workstation", original.operations[0].workstation))
    workstation.workstation_name = prefix
    workstation.status = "Off"
    workstation.insert()

    frappe.set_user(approval_actors[0])
    order = frappe.copy_doc(original)
    order.docstatus = 0
    order.status = "Draft"
    order.workflow_state = "草稿"
    for field in ("approval_requested_by", "approval_reviewed_by", "approval_note", "amended_from",
                  "previous_work_order", "actual_start_date", "actual_end_date"):
        order.set(field, None)
    for field in ("produced_qty", "material_transferred_for_manufacturing", "process_loss_qty",
                  "actual_operating_cost", "corrective_operation_cost", "lead_time"):
        order.set(field, 0)
    for row in order.operations:
        row.docstatus = 0
        row.status = "Pending"
        row.workstation = workstation.name
        for field in ("completed_qty", "process_loss_qty", "actual_operation_time", "actual_operating_cost"):
            row.set(field, 0)
        row.actual_start_time = row.actual_end_time = None
        for field in ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency",
                      "report_employee", "report_department"):
            row.set(field, None)
        row.report_scope = ""
    order.operations[0].report_scope = "DEPT"
    order.operations[0].report_department = original.production_team
    for row in order.required_items:
        row.docstatus = 0
        for field in ("transferred_qty", "consumed_qty", "returned_qty"):
            row.set(field, 0)
    order.insert(set_name=prefix)
    for actor, action in zip(approval_actors, ("送审", "审核通过", "签批通过")):
        frappe.set_user(actor)
        apply_production_approval(order.name, action, str(order.modified))
        order.reload()
    assert order.docstatus == 1 and order.workflow_state == "已批准"
    frappe.set_user("Administrator")
    add_user_permission("Work Order", order.name, user)
    sample = {"site": template["site"], "base_url": "http://127.0.0.1:18090",
        "actors": {"A": {"user": user, "employee": employee.name, "keys": keys}},
        "cases": {"I05": {"order": order.name, "operation_id": order.operations[0].name,
            "request_id": frappe.generate_hash(length=32), "inputs": {"work_order": order.name,
            "operation_id": order.operations[0].name, "from_time": "2026-10-27 09:00:00",
            "to_time": "2026-10-27 10:00:00", "good_quantity": 2, "bad_quantity": 0,
            "shutdown_seconds": 0, "overtime_seconds": 0}}}}
    frappe.set_user(user)
    permissions = []
    for doctype, permission, doc, expected in (("Work Order", "read", order, True),
        ("Work Order", "write", order, False), ("Stock Entry", "create", None, False),
        ("Job Card", "create", None, True), ("Job Card", "write", None, True), ("Job Card", "submit", None, True)):
        actual = bool(frappe.has_permission(doctype, permission, doc=doc))
        permissions.append({"doctype": doctype, "permission": permission, "actual": actual, "expected": expected})
        assert actual == expected, "Narrow actor permission contract failed"
    frappe.set_user("Administrator")
    state = case_state(sample, "I05")
    assert not any(row.get("report_request_id") for row in state["cards"]) and not state["logs"]
    assert all(not row.completed_qty and not row.process_loss_qty for row in order.operations)
    retention = {group: compare_tables(rows) for group, rows in baseline.items()}
    assert all(preserved(rows) for rows in retention.values()), "Setup changed pre-existing rows"
    assert all(retention["business"][name]["new_rows"] == 0 for name in STOCK)
    write_private(PRIVATE / "setup-state.json", state)
    write_private(PRIVATE / "fixture.json", sample)
    frappe.db.commit()
    return {"fixture_ready": True, "runtime_before_setup": runtime, "new_user_employee_workstation_order_each": 1,
            "plan": 10, "operations": 3, "initial_report_facts": 0, "permissions": permissions,
            "retention": retention, "old_rows_unchanged": True, "http_confirmations_sent": 0}


def observe(sample, label):
    # Each invocation is a new process and DB connection; no previous read snapshot is reused.
    isolation = frappe.db.sql("select @@tx_isolation")[0][0]
    assert isolation.upper().replace("_", "-") in ("REPEATABLE-READ", "READ-COMMITTED", "SERIALIZABLE")
    state = case_state(sample, "I05")
    observed = {"fresh_process_and_connection": True, "isolation": isolation,
                "connection_id_sha256": digest(frappe.db.sql("select connection_id()")[0][0])}
    if label == "committed":
        data = sample["cases"]["I05"]
        facts = [row for row in state["cards"] if row.get("report_request_id") == data["request_id"]]
        assert len(facts) == 1 and facts[0]["docstatus"] == 1 and facts[0]["total_completed_qty"] == 2
        logs = [row for row in state["logs"] if row["parent"] == facts[0]["name"]]
        assert len(logs) == 1 and logs[0]["completed_qty"] == 2 and logs[0]["time_in_mins"] == 60
        operation = next(row for row in state["order"]["operations"] if row["name"] == data["operation_id"])
        assert operation["completed_qty"] == 2 and operation["actual_operation_time"] == 60
        observed["submitted_fact_time_and_parent_visible"] = True
    write_private(PRIVATE / (label + ".json"), state)
    return {"label": label, "state_sha256": digest(state), "database_read_only": True, **observed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("source", "setup", "snapshot", "preserve"))
    parser.add_argument("label", nargs="?", choices=("before", "committed", "after"))
    args = parser.parse_args()
    runtime = source_state()
    if args.mode == "source":
        print(json.dumps(runtime, ensure_ascii=False))
        return
    os.umask(0o077)
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    PRIVATE.chmod(0o700)
    os.chdir("sites")
    frappe.init(site="xgd-b08-http.localhost")
    frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user("Administrator")
        if args.mode == "setup":
            result = setup(runtime)
        elif args.mode == "snapshot":
            assert args.label
            result = observe(json.loads((PRIVATE / "fixture.json").read_text()), args.label)
        else:
            baseline = json.loads((PRIVATE / "baseline.json").read_text())
            groups = {group: compare_tables(rows) for group, rows in baseline.items()}
            result = {"groups": groups, "all_old_rows_unchanged": all(preserved(rows) for rows in groups.values())}
            assert result["all_old_rows_unchanged"], "Old data retention failed"
            assert all(groups["business"][name]["new_rows"] == 0 for name in STOCK), "Unexpected inventory additions"
            result["stock_new_rows"] = 0
        print(json.dumps(result, ensure_ascii=False))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
