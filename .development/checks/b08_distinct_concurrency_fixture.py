"""Dedicated I03/I04 samples and read-only observations; never replay a setup.

Runs in the existing B08 bench container. All identifiers, credentials and row
hash baselines remain private. Every mode except setup is read-only to the DB.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import erpnext
import frappe

PRIVATE = Path("/tmp/b08-distinct-concurrency-private")
MANIFEST = Path("/b01/b08-distinct-concurrency-source-manifest.json")
BUSINESS = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log",
            "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment"]
SECURITY = ["User", "Role", "Has Role", "User Permission", "Custom DocPerm"]
EXTRA = ["Employee", "Production Time Rule", "Production Time Period", "Workstation"]
STOCK = ["Stock Entry", "Stock Entry Detail", "Stock Ledger Entry"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     default=str, separators=(",", ":")).encode()).hexdigest()


def write_private(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")
    path.chmod(0o600)


def source_state():
    manifest = json.loads(MANIFEST.read_text())
    root = Path(erpnext.__file__).resolve().parent.parent
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in manifest["files"]}
    assert len(actual) == 33 and actual == manifest["files"], "Installed source must match the approved 33-file manifest"
    return {"manifest": manifest, "manifest_file_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "runtime_files_match": True, "runtime_files": actual,
            "erpnext_version": erpnext.__version__, "frappe_version": frappe.__version__,
            "scripts": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                        for name in ("b08_distinct_concurrency_fixture.py", "b08_distinct_concurrency_http.py")}}


def capture_tables(doctypes):
    result = {}
    for doctype in doctypes:
        columns = sorted(frappe.db.get_table_columns(doctype))
        rows = frappe.get_all(doctype, fields=columns, order_by="name", limit_page_length=0)
        result[doctype] = {"columns": columns, "rows": {r.name: digest(dict(r)) for r in rows}}
    return result


def compare_tables(baseline):
    result = {}
    for doctype, before in baseline.items():
        after = {r.name: digest(dict(r)) for r in frappe.get_all(
            doctype, fields=before["columns"], order_by="name", limit_page_length=0)}
        result[doctype] = {"old_rows": len(before["rows"]),
                           "missing": sum(name not in after for name in before["rows"]),
                           "changed": sum(name in after and value != after[name] for name, value in before["rows"].items()),
                           "new_rows": len(set(after) - set(before["rows"]))}
    return result


def preserved(summary):
    return all(not item["missing"] and not item["changed"] for item in summary.values())


def case_state(sample, case):
    order = frappe.get_doc("Work Order", sample["cases"][case]["order"])
    cards = frappe.get_all("Job Card", filters={"work_order": order.name}, fields=["*"], order_by="name", limit_page_length=0)
    names = [r.name for r in cards]
    logs = frappe.get_all("Job Card Time Log", filters={"parent": ["in", names]}, fields=["*"], order_by="name", limit_page_length=0)
    return {"order": order.as_dict(), "cards": [dict(r) for r in cards], "logs": [dict(r) for r in logs],
            "operation_cost_precisions": {row.name: row.precision("actual_operating_cost") for row in order.operations},
            "stock": capture_tables(STOCK),
            "global_cards": capture_tables(["Job Card"])["Job Card"],
            "global_time_logs": [dict(row) for row in frappe.get_all("Job Card Time Log", fields=["*"],
                                                                   order_by="name", limit_page_length=0)]}


def create_fixture(runtime):
    from frappe.core.doctype.user.user import generate_keys
    from frappe.permissions import add_user_permission
    from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
    from erpnext.manufacturing.doctype.job_card.job_card import preview_production_report_time, confirm_production_report

    assert not (PRIVATE / "fixture.json").exists() and not (PRIVATE / "before.json").exists(), "Never recreate a consumed or failed setup"
    write_private(PRIVATE / "setup-source.json", runtime)
    baseline = {"business": capture_tables(BUSINESS), "security": capture_tables(SECURITY), "extra": capture_tables(EXTRA)}
    write_private(PRIVATE / "before.json", baseline)
    source = json.loads(Path("/tmp/b08-private/fixture.json").read_text())
    original = frappe.get_doc("Work Order", source["order"])
    assert original.qty == 10 and len(original.operations) == 3
    assert not any(original.get(f) for f in ("sales_order", "sales_order_item", "material_request",
                   "material_request_item", "production_plan", "production_plan_item", "production_plan_sub_assembly_item"))
    actors = [original.approval_requested_by, original.approval_reviewed_by,
              source["user"].replace("-report@", "-director@")]
    for actor, role in zip(actors, ("生产工单发起", "生产工单审核", "生产工单签批")):
        assert role in frappe.get_roles(actor)
    prefix = "b08-distinct-" + frappe.generate_hash(length=10)
    sample = {"site": source["site"], "base_url": "http://127.0.0.1:18090", "prefix": prefix,
              "actors": {}, "cases": {}}
    for alias in ("A", "B"):
        user = prefix + "-" + alias.lower() + "@example.invalid"
        frappe.get_doc({"doctype": "User", "email": user, "first_name": "并发报工验收" + alias,
                       "language": "zh", "enabled": 1, "send_welcome_email": 0, "user_type": "System User",
                       "roles": [{"role": "生产报工"}]}).insert()
        employee = frappe.get_doc({"doctype": "Employee", "first_name": "并发报工验收" + alias, "gender": "Male",
                                  "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
                                  "company": original.company, "department": original.production_team,
                                  "status": "Active", "user_id": user, "create_user_permission": 0}).insert()
        add_user_permission("Company", original.company, user)
        add_user_permission("Department", original.production_team, user, applicable_for="Work Order")
        sample["actors"][alias] = {"user": user, "employee": employee.name, "keys": generate_keys(user)}
        assert "System Manager" not in frappe.get_roles(user)
        assert frappe.db.count("Employee", {"user_id": user, "status": "Active"}) == 1

    for case, day in (("I03", "2026-10-25"), ("I04", "2026-10-26")):
        workstation = frappe.copy_doc(frappe.get_doc("Workstation", original.operations[0].workstation))
        workstation.workstation_name = prefix + "-" + case
        workstation.status = "Off"
        workstation.insert()
        frappe.set_user(actors[0])
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
        order.insert(set_name=prefix + "-" + case.lower())
        for actor, action in zip(actors, ("送审", "审核通过", "签批通过")):
            frappe.set_user(actor)
            apply_production_approval(order.name, action, str(order.modified))
            order.reload()
        assert order.docstatus == 1 and order.workflow_state == "已批准"
        frappe.set_user("Administrator")
        for data in sample["actors"].values():
            add_user_permission("Work Order", order.name, data["user"])
        sample["cases"][case] = {"order": order.name, "operation_id": order.operations[0].name,
            "business_day": day, "requests": {alias: frappe.generate_hash(length=32) for alias in ("A", "B")},
            "inputs": {alias: {"work_order": order.name, "operation_id": order.operations[0].name,
                       "from_time": day + (" 09:00:00" if alias == "A" else " 10:00:00"),
                       "to_time": day + (" 10:00:00" if alias == "A" else " 11:00:00"),
                       "good_quantity": 2 if case == "I03" else 1, "bad_quantity": 0,
                       "shutdown_seconds": 0, "overtime_seconds": 0} for alias in ("A", "B")}}
        frappe.set_user(sample["actors"]["A"]["user"])
        initial = {"work_order": order.name, "operation_id": order.operations[0].name,
                   "from_time": day + " 08:00:00", "to_time": day + " 09:00:00", "good_quantity": 8,
                   "bad_quantity": 0, "shutdown_seconds": 0, "overtime_seconds": 0}
        preview = preview_production_report_time(**initial)
        result = confirm_production_report(**initial, request_id=prefix + "-" + case.lower() + "-base",
                                           context_fingerprint=preview["context_fingerprint"])
        sample["cases"][case]["baseline_card"] = result["name"]
        order.reload()
        assert order.qty == 10 and order.operations[0].completed_qty == 8 and order.operations[0].process_loss_qty == 0
        assert all(not row.completed_qty and not row.process_loss_qty for row in order.operations[1:])
        frappe.set_user("Administrator")

    permissions = []
    for alias, actor in sample["actors"].items():
        frappe.set_user(actor["user"])
        for case, data in sample["cases"].items():
            order = frappe.get_doc("Work Order", data["order"])
            for doctype, permission, expected, doc in (
                ("Work Order", "read", True, order), ("Work Order", "write", False, order),
                ("Stock Entry", "create", False, None), ("Job Card", "create", True, None),
                ("Job Card", "write", True, data["baseline_card"]), ("Job Card", "submit", True, data["baseline_card"]),
            ):
                actual = bool(frappe.has_permission(doctype, permission, doc=doc))
                permissions.append({"actor": alias, "case": case, "doctype": doctype,
                                    "permission": permission, "expected": expected, "actual": actual})
                assert actual == expected, "Narrow actor permissions differ from the required contract"
    frappe.set_user("Administrator")
    retention = {group: compare_tables(captured) for group, captured in baseline.items()}
    assert all(preserved(group) for group in retention.values()), "Existing rows changed during setup"
    assert all(retention["business"][dt]["new_rows"] == 0 for dt in STOCK)
    for case in sample["cases"]:
        write_private(PRIVATE / (case + "-setup-state.json"), case_state(sample, case))
    write_private(PRIVATE / "fixture.json", sample)
    frappe.db.commit()
    return {"fixture_ready": True, "source_before_setup": runtime, "new_users": 2, "new_employees": 2,
            "new_work_orders": 2, "new_workstations": 2, "new_baseline_facts": 2,
            "plan_each": 10, "baseline_good_each": 8, "scope": "DEPT", "permissions": permissions,
            "old_data_retention": retention, "old_rows_unchanged": True, "stock_additions": 0,
            "concurrency_requests_executed": 0, "credentials_printed": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("source", "setup", "snapshot", "preserve"))
    parser.add_argument("case", nargs="?", choices=("I03", "I04"))
    parser.add_argument("label", nargs="?", choices=("before", "after"))
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
            result = create_fixture(runtime)
        elif args.mode == "snapshot":
            assert args.case and args.label
            sample = json.loads((PRIVATE / "fixture.json").read_text())
            state = case_state(sample, args.case)
            write_private(PRIVATE / (args.case + "-" + args.label + ".json"), state)
            result = {"case": args.case, "label": args.label, "state_sha256": digest(state), "database_read_only": True}
        else:
            baseline = json.loads((PRIVATE / "before.json").read_text())
            groups = {group: compare_tables(rows) for group, rows in baseline.items()}
            result = {"groups": groups, "all_old_rows_unchanged": all(preserved(group) for group in groups.values())}
            assert result["all_old_rows_unchanged"], "Old data retention failed; inspect privately"
        print(json.dumps(result, ensure_ascii=False))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
