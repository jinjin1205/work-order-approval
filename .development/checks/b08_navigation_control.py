"""Only the newly isolated B08 navigation case; never replay reports."""
import hashlib
import json
import os
import sys
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission

os.chdir("sites")
p = Path("/tmp/b08-private")
f = p / "b08-navigation-ui.json"
a = json.loads(f.read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    assert a["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    assert a["actors"]["reporter"]["user"].startswith("b06-task-")
    frappe.set_user("Administrator")
    order = frappe.get_doc("Work Order", a["order"])
    mode = sys.argv[1]
    if mode == "sibling":
        assert not a.get("sibling"), "Do not recreate the sibling"
        frappe.set_user(a["actors"]["editor"]["user"])
        sibling = frappe.get_doc({"doctype": "Work Order", **{k: order.get(k) for k in (
            "production_item", "bom_no", "company", "production_team", "qty", "stock_uom",
            "expected_delivery_date", "planned_start_date", "source_warehouse", "wip_warehouse", "fg_warehouse")}}).insert()
        assert not sibling.operations and not sibling.required_items
        frappe.set_user("Administrator")
        add_user_permission("Work Order", sibling.name, a["actors"]["reporter"]["user"])
        a["sibling"] = sibling.name
        frappe.db.commit()
        f.write_text(json.dumps(a, ensure_ascii=False, indent=2))
        print(json.dumps({"new_empty_sibling": 1, "reports_written": 0}))
    elif mode == "revoke":
        employee = frappe.get_doc("Employee", a["employee"])
        assert employee.user_id == a["actors"]["reporter"]["user"]
        employee.user_id = None
        employee.save()
        frappe.db.commit()
        print(json.dumps({"new_fixture_employee_unbound": True, "old_roles_unchanged": True}))
    else:
        assert mode in ("state", "audit")
        reports = frappe.get_all("Job Card", filters={"work_order": order.name, "report_request_id": ["is", "set"]}, fields=["name", "docstatus", "operation_id", "total_completed_qty", "process_loss_qty"])
        if mode == "audit":
            old = json.loads((p / "b08-navigation-before.json").read_text())
            additions = {}
            for dt, base in old.items():
                current = {r.name: hashlib.sha256(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
                    for r in frappe.get_all(dt, fields=base["columns"], limit_page_length=0)}
                assert all(current.get(n) == h for n, h in base["rows"].items()), dt + " old row changed"
                additions[dt] = len(set(current) - set(base["rows"]))
            assert len(reports) == 2 and all(r.docstatus == 1 and r.total_completed_qty == 1 and r.process_loss_qty == 0 and r.operation_id == order.operations[0].name for r in reports)
            assert [r.completed_qty for r in order.operations] == [2, 0, 0]
            assert [float(r.report_plan_qty) for r in order.operations] == [2, 2, 1]
            assert order.qty == 10 and order.produced_qty == 0
            assert all(r.workstation == a["workstation"] for r in order.operations)
            assert additions["Work Order"] == 2 and additions["Job Card"] == 5 and additions["Job Card Time Log"] == 2
            assert all(additions[dt] == 0 for dt in ("Stock Entry", "Stock Entry Detail", "Stock Ledger Entry"))
            print(json.dumps({"old_tables_preserved": len(old), "old_rows_changed": 0, "effective_reports": 2, "time_logs": 2,
                "new_stock_documents": 0, "plans": [2, 2, 1], "completed": [2, 0, 0], "new_work_orders": 2,
                "new_users": additions["User"], "new_roles": additions["Role"], "new_employees": additions["Employee"],
                "independent_workstation": True, "old_users_roles_permissions_preserved": True}))
        else:
            print(json.dumps({"reports": len(reports), "completed": [r.completed_qty for r in order.operations], "status": order.status}))
finally:
    frappe.db.rollback()
    frappe.destroy()
