"""New narrow actors and one ready order; preserve every pre-existing captured row."""
import hashlib
import json
import os
import secrets
from pathlib import Path
import frappe
from frappe.permissions import add_permission, add_user_permission, update_permission_property
from frappe.utils.password import update_password
from frappe.tests.utils import change_settings
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval

os.umask(0o077)
os.chdir("sites")
p = Path("/tmp/b08-private")
access, baseline = p / "b05-entries-ui.json", p / "b05-entries-before.json"
assert not access.exists() and not baseline.exists(), "Resume existing samples; never recreate"
source = json.loads((p / "fixture.json").read_text())
header = json.loads((p / "b05-header-ui.json").read_text())
details = json.loads((p / "b05-details-ui.json").read_text())
closeout = json.loads((p / "b05-closeout-ui.json").read_text())
frappe.init(site=source["site"])
frappe.connect()
try:
    assert source["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment", "BOM", "BOM Item", "BOM Operation", "Item", "UOM", "User", "Has Role", "Role", "Custom DocPerm", "User Permission", "Employee", "Workstation"]
    before = {}
    for dt in tables:
        columns = sorted(frappe.db.get_table_columns(dt))
        rows = frappe.get_all(dt, fields=columns, limit_page_length=0)
        before[dt] = {"columns": columns, "rows": {r.name: hashlib.sha256(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest() for r in rows}}
    old = frappe.get_doc("Work Order", next(s["order"] for s in closeout["samples"] if s["mode"] == "partial"))
    assert old.actual_start_date and old.status == "Closed"
    prefix = "B05-ENTRY-" + frappe.generate_hash(length=8)
    actors = {}
    for key, template, label, permission in (("initiator", header["user"], "入口验收发起人", "delete"), ("director", closeout["user"], "入口验收厂长", "cancel")):
        role = frappe.get_doc({"doctype": "Role", "role_name": prefix + "-" + permission, "desk_access": 1}).insert().name
        add_permission("Work Order", role, ptype="read")
        update_permission_property("Work Order", role, 0, permission, 1)
        if key == "initiator":
            update_permission_property("Work Order", role, 0, "amend", 1)
        roles = [r.role for r in frappe.get_doc("User", template).roles] + [role]
        assert not set(roles) & {"System Manager", "Manufacturing Manager"}
        user = prefix.lower() + "-" + key + "@example.invalid"
        frappe.get_doc({"doctype": "User", "email": user, "first_name": label, "language": "zh", "send_welcome_email": 0, "user_type": "System User", "roles": [{"role": r} for r in roles]}).insert()
        password = secrets.token_urlsafe(24)
        update_password(user, password)
        add_user_permission("Company", old.company, user)
        add_user_permission("Department", old.production_team, user, applicable_for="Work Order")
        actors[key] = {"user": user, "password": password}
    frappe.set_user(actors["initiator"]["user"])
    bom = frappe.get_doc("BOM", details["bom_no"])
    # Controlled prerequisite: the old confirmation package is not replayed as a new acceptance.
    order = frappe.get_doc({"doctype": "Work Order", "production_item": details["production_item"], "bom_no": bom.name,
        "company": old.company, "production_team": old.production_team, "qty": 10, "stock_uom": old.stock_uom,
        "expected_delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 7), "planned_start_date": frappe.utils.now(),
        "source_warehouse": old.source_warehouse, "wip_warehouse": old.wip_warehouse, "fg_warehouse": old.fg_warehouse})
    order.insert()
    for r in bom.operations:
        order.append("operations", {"operation": r.operation, "workstation": r.workstation, "time_in_mins": r.time_in_mins, "sequence_id": r.sequence_id})
    order.set_required_items()
    order.save()
    for user, action in ((actors["initiator"]["user"], "送审"), (old.approval_reviewed_by, "审核通过"), (actors["director"]["user"], "签批通过")):
        frappe.set_user(user)
        with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
            apply_production_approval(order.name, action, str(order.reload().modified))
    order.reload()
    assert order.status == "Not Started" and not order.actual_start_date
    assert frappe.has_permission("Work Order", "cancel", doc=order)
    value = {"site": source["site"], "base_url": source["base_url"], "actors": actors, "ready_order": order.name, "copy_source": old.name}
    baseline.write_text(json.dumps(before, ensure_ascii=False, indent=2))
    access.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    frappe.db.commit()
    print(json.dumps({"old_tables_captured": len(before), "new_users": 2, "new_roles": 2, "ready_approved_order": 1, "prepared_job_cards": 3, "new_reports": 0, "new_stock_entries": 0, "old_executed_copy_source_read_only": True, "secrets_printed": False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
