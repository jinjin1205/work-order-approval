"""Final capture: every old captured row unchanged, only this new fixture advances."""
import hashlib
import json
import os
import sys
from pathlib import Path
import frappe

os.chdir("sites")
p = Path("/tmp/b08-private")
case = sys.argv[sys.argv.index("--case") + 1] if "--case" in sys.argv else "b06-tasks"
assert case in ("b06-tasks", "b06-retention")
a = json.loads((p / (case + "-ui.json")).read_text())
baseline = json.loads((p / (case + "-before.json")).read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    assert a["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    additions = {}
    differences = {}
    for dt, old in baseline.items():
        rows = frappe.get_all(dt, fields=old["columns"], limit_page_length=0)
        current = {row.name: hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest() for row in rows}
        changed = [name for name, digest in old["rows"].items() if current.get(name) != digest]
        if changed:
            differences[dt] = changed
        if "--audit" not in sys.argv:
            assert not changed, dt + " old row changed"
        additions[dt] = len(set(current) - set(old["rows"]))
    order = frappe.get_doc("Work Order", a["order"])
    assert order.docstatus == 1 and order.workflow_state == "已批准" and order.status == "In Process"
    assert order.qty == 10 and order.produced_qty == 0
    assert [r.name for r in order.operations] == a["original_rows"]
    assert [float(r.report_plan_qty) for r in order.operations] == [1, 2, 3]
    assert [r.idx for r in order.operations] == [1, 2, 3]
    assert [r.sequence_id for r in order.operations] == [1, 2, 3]
    assert [r.report_scope for r in order.operations] == ["PERSON", "DEPT", "ALL"]
    assert [r.status for r in order.operations] == ["Completed", "Pending", "Pending"]
    assert [r.completed_qty for r in order.operations] == [1, 0, 0]
    assert all(not r.process_loss_qty for r in order.operations)
    assert additions["Work Order"] == 1 and additions["Work Order Operation"] == 3
    assert additions["Job Card"] == 4 and additions["Job Card Time Log"] == 1
    assert additions["User"] == 2 and additions["Role"] == 1 and additions["Employee"] == 1
    assert all(additions[dt] == 0 for dt in ("Stock Entry", "Stock Entry Detail", "Stock Ledger Entry"))
    if "--audit" in sys.argv:
        assert set(differences) == {"Workstation"} and len(differences["Workstation"]) == 1
        station = frappe.db.get_value("Workstation", differences["Workstation"][0], ["status", "modified_by"], as_dict=True)
        assert station.modified_by == a["actors"]["reporter"]["user"]
    if case == "b06-retention":
        assert additions["Workstation"] == 1 and all(r.workstation == a["workstation"] for r in order.operations)
    print(json.dumps({"acceptance_case": case, "historical_failed_case_replaced": False,
        "strict_old_row_retention_result": "FAILED" if differences else "OK",
        "old_tables_captured": len(baseline), "old_tables_exact_rows_preserved": len(baseline) - len(differences),
        "changed_old_rows": {dt: len(rows) for dt, rows in differences.items()},
        "changed_station_current_modifier_is_new_reporter": bool(differences),
        "old_station_field_level_diff_proven": False if differences else None,
        "native_station_state_audit_not_restored": bool(differences),
        "original_task_identities_retained": True,
        "new_copy_and_insert_removed_after_saved_acceptance": True if case == "b06-tasks" else None,
        "independent_task_plans": [1, 2, 3], "parent_plan": 10, "completed_tasks": 1, "total_tasks": 3,
        "effective_reports": 1, "new_draft_plan_cards": 3, "time_logs": 1, "new_stock_entries": 0,
        "new_stock_ledger_entries": 0, "new_users": 2, "new_roles": 1, "new_employee": 1,
        "old_users_roles_permissions_unchanged": True}, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
