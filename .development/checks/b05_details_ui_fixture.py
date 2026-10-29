"""New bounded UI actors and BOM; preserve all captured existing rows."""
import hashlib
import json
import os
import secrets
from pathlib import Path
import frappe
from frappe.permissions import add_permission, add_user_permission
from frappe.utils.password import update_password
os.umask(0o077)
os.chdir("sites")
private = Path("/tmp/b08-private")
access = private / "b05-details-ui.json"
baseline = private / "b05-details-before.json"
assert not access.exists() and not baseline.exists(), "Keep the existing run; never recreate it"
source = json.loads((private / "fixture.json").read_text())
frappe.init(site=source["site"])
frappe.connect()
try:
    assert source["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment", "BOM", "BOM Item", "BOM Operation", "Item", "UOM", "User", "Has Role", "Role", "Custom DocPerm", "User Permission"]
    def digest(row):
        return hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    before = {}
    for dt in tables:
        columns = sorted(frappe.db.get_table_columns(dt))
        before[dt] = {"columns": columns, "rows": {row.name: digest(row) for row in frappe.get_all(dt, fields=columns, limit_page_length=0)}}
    baseline.write_text(json.dumps(before, ensure_ascii=False, indent=2))
    old = frappe.get_doc("Work Order", source["order"])
    prefix = "B05-" + frappe.generate_hash(length=8)
    role = prefix + "明细只读资料"
    frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()
    for dt in ("Item", "BOM", "Company", "Department", "Warehouse", "Operation", "Workstation", "UOM"):
        add_permission(dt, role, ptype="read")
    add_permission("Project", role, ptype="select")
    initiator = frappe.get_doc("User", old.approval_requested_by)
    roles = [row.role for row in initiator.roles] + [role]
    assert "生产工单发起" in roles and not set(roles) & {"System Manager", "Manufacturing Manager", "生产工单签批"}
    user = prefix.lower() + "@example.invalid"
    frappe.get_doc({"doctype": "User", "email": user, "first_name": "明细确认验收员", "language": "zh", "send_welcome_email": 0,
        "user_type": "System User", "roles": [{"role": value} for value in roles]}).insert()
    password = secrets.token_urlsafe(24)
    update_password(user, password)
    add_user_permission("Company", old.company, user)
    add_user_permission("Department", old.production_team, user, applicable_for="Work Order")
    unit = frappe.get_doc({"doctype": "UOM", "uom_name": prefix + "-千克", "must_be_whole_number": 0}).insert().name
    group = frappe.db.get_value("Item", old.production_item, "item_group")
    raw = frappe.get_doc({"doctype": "Item", "item_code": prefix + "-原料", "item_group": group,
        "stock_uom": unit, "is_stock_item": 1, "valuation_method": "Moving Average"}).insert()
    fg = frappe.get_doc({"doctype": "Item", "item_code": prefix + "-成品", "item_group": group,
        "stock_uom": old.stock_uom, "is_stock_item": 1}).insert()
    bom = frappe.get_doc({"doctype": "BOM", "item": fg.name, "quantity": 1, "company": old.company,
        "currency": frappe.get_cached_value("Company", old.company, "default_currency"), "with_operations": 1,
        "items": [{"item_code": raw.name, "qty": 0.5, "source_warehouse": old.source_warehouse}],
        "operations": [{"operation": row.operation, "workstation": row.workstation, "time_in_mins": 1, "sequence_id": i}
            for i,row in enumerate(old.operations,1)]}).insert().submit()
    assert len(bom.operations) == 3
    value = {"site": source["site"], "base_url": "http://127.0.0.1:18090", "user": user, "password": password,
        "company": old.company, "production_team": old.production_team, "production_item": fg.name,
        "bom_no": bom.name, "qty": 10, "source_warehouse": old.source_warehouse,
        "wip_warehouse": old.wip_warehouse, "fg_warehouse": old.fg_warehouse, "raw": raw.name, "unit": unit}
    access.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    frappe.db.commit()
    print(json.dumps({"new_narrow_initiator": True, "independent_bom_operations": 3, "unit_use": 0.5, "old_tables_captured": len(tables), "business_orders_created": 0, "secrets_printed": False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
