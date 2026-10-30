"""One new task-edit order, editor and narrow reporter; keep all captured old rows."""
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
import frappe
from frappe.permissions import add_permission, add_user_permission
from frappe.utils.password import update_password

os.umask(0o077)
os.chdir("sites")
p = Path("/tmp/b08-private")
case = sys.argv[1] if len(sys.argv) > 1 else "b06-tasks"
assert case in ("b06-tasks", "b06-retention", "b08-navigation", "b08-quality", "b09-lifecycle")
access, baseline = p / (case + "-ui.json"), p / (case + "-before.json")
assert not access.exists() and not baseline.exists(), "Resume existing B06 fixture; do not recreate"
source = json.loads((p / "fixture.json").read_text())
entries = json.loads((p / "b05-entries-ui.json").read_text())
details = json.loads((p / "b05-details-ui.json").read_text())
frappe.init(site=source["site"])
frappe.connect()
try:
    assert source["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment", "BOM", "BOM Item", "BOM Operation", "Item", "UOM", "User", "Has Role", "Role", "Custom DocPerm", "User Permission", "Employee", "Workstation"]
    if case in ("b08-quality", "b09-lifecycle"):
        tables += ["Quality Inspection", "Quality Inspection Reading", "File"]
    if case == "b09-lifecycle":
        tables += ["DocShare"]
    before = {}
    for dt in tables:
        columns = sorted(frappe.db.get_table_columns(dt))
        rows = frappe.get_all(dt, fields=columns, limit_page_length=0)
        before[dt] = {"columns": columns, "rows": {row.name: hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest() for row in rows}}
        if dt == "Workstation":
            before[dt]["raw_rows"] = {row.name: dict(row) for row in rows}
    old = frappe.get_doc("Work Order", entries["copy_source"])
    prefix = "B06-TASK-" + frappe.generate_hash(length=8)
    bom = frappe.get_doc("BOM", details["bom_no"])
    station = frappe.copy_doc(frappe.get_doc("Workstation", bom.operations[0].workstation), ignore_no_copy=False)
    station.workstation_name = prefix + "-独立工位"
    station.insert()
    # New fixture-only select role: no change to prior role matrices or customer deployment.
    select_role = frappe.get_doc({"doctype": "Role", "role_name": prefix + "-select", "desk_access": 1}).insert().name
    for dt in ("Employee", "Department"):
        add_permission(dt, select_role, ptype="select")
    editor_roles = [r.role for r in frappe.get_doc("User", entries["actors"]["initiator"]["user"]).roles] + [select_role]
    assert not set(editor_roles) & {"System Manager", "Manufacturing Manager"}
    actors = {}
    for key, label, roles in (("editor", "任务调整验收员", editor_roles), ("reporter", "任务计划报工员", ["生产报工"])):
        user = prefix.lower() + "-" + key + "@example.invalid"
        doc = frappe.get_doc({"doctype": "User", "email": user, "first_name": label, "language": "zh", "time_zone": "Asia/Shanghai",
            "send_welcome_email": 0, "user_type": "System User", "roles": [{"role": role} for role in roles]}).insert()
        password = secrets.token_urlsafe(24)
        update_password(user, password)
        api_key, api_secret = frappe.generate_hash(length=15), frappe.generate_hash(length=32)
        doc.reload()
        doc.api_key, doc.api_secret = api_key, api_secret
        doc.save()
        add_user_permission("Company", old.company, user)
        add_user_permission("Department", old.production_team, user, applicable_for="Work Order")
        actors[key] = {"user": user, "password": password, "api_key": api_key, "api_secret": api_secret}
    employee = frappe.get_doc({"doctype": "Employee", "first_name": "任务计划报工员", "gender": "Male", "date_of_birth": "1990-01-01",
        "date_of_joining": "2020-01-01", "company": old.company, "department": old.production_team, "status": "Active",
        "user_id": actors["reporter"]["user"], "create_user_permission": 0}).insert().name
    frappe.set_user(actors["editor"]["user"])
    order = frappe.get_doc({"doctype": "Work Order", "production_item": details["production_item"], "bom_no": bom.name,
        "company": old.company, "production_team": old.production_team, "qty": 10, "stock_uom": old.stock_uom,
        "expected_delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 7), "planned_start_date": frappe.utils.now(),
        "source_warehouse": old.source_warehouse, "wip_warehouse": old.wip_warehouse, "fg_warehouse": old.fg_warehouse}).insert()
    for row in bom.operations:
        order.append("operations", {"operation": row.operation, "workstation": station.name, "time_in_mins": row.time_in_mins,
            "sequence_id": row.sequence_id, "report_scope": "ALL"})
    order.set_required_items()
    order.save()
    assert len(order.operations) == 3 and all(float(r.report_plan_qty) == 10 for r in order.operations)
    frappe.set_user("Administrator")
    add_user_permission("Work Order", order.name, actors["reporter"]["user"])
    frappe.set_user(actors["reporter"]["user"])
    assert order.has_permission("read") and not order.has_permission("write")
    value = {"site": source["site"], "base_url": source["base_url"], "actors": actors, "employee": employee,
        "order": order.name, "company": old.company, "department": old.production_team,
        "original_rows": [r.name for r in order.operations], "operations": [r.operation for r in order.operations],
        "reviewer": old.approval_reviewed_by, "director": entries["actors"]["director"]["user"], "workstation": station.name}
    baseline.write_text(json.dumps(before, ensure_ascii=False, indent=2, default=str))
    access.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    frappe.db.commit()
    print(json.dumps({"old_tables_captured": len(before), "new_users": 2, "new_roles": 1, "new_employee": 1,
        "prepared_draft": 1, "tasks": 3, "reports": 0, "inventory": 0, "independent_workstation": 1,
        "narrow_reporter_no_order_write": True, "secrets_printed": False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
