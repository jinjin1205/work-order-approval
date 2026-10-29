"""New B07 masters/resources and actors only; capture old rows plus Bin."""
import hashlib
import json
import os
import secrets
from pathlib import Path
import frappe
from frappe.permissions import add_permission, add_user_permission, update_permission_property
from frappe.utils.password import update_password

os.umask(0o077)
os.chdir("sites")
p = Path("/tmp/b08-private")
access, baseline = p / "b07-materials-ui.json", p / "b07-materials-before.json"
assert not access.exists() and not baseline.exists(), "Never replace an existing B07 run"
source = json.loads((p / "fixture.json").read_text())
entries = json.loads((p / "b05-entries-ui.json").read_text())
details = json.loads((p / "b05-details-ui.json").read_text())
frappe.init(site=source["site"])
frappe.connect()
try:
    assert source["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment", "BOM", "BOM Item", "BOM Operation", "Item", "UOM", "User", "Has Role", "Role", "Custom DocPerm", "User Permission", "Employee", "Workstation", "Bin"]
    before = {}
    for dt in tables:
        columns = sorted(frappe.db.get_table_columns(dt))
        rows = frappe.get_all(dt, fields=columns, limit_page_length=0)
        before[dt] = {"columns": columns, "rows": {r.name: hashlib.sha256(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest() for r in rows}}
        if dt in ("Workstation", "BOM", "BOM Item", "Bin"):
            before[dt]["raw_rows"] = {r.name: dict(r) for r in rows}
    old = frappe.get_doc("Work Order", entries["copy_source"])
    prefix = "B07-MAT-" + frappe.generate_hash(length=8)
    template = frappe.get_doc("BOM", details["bom_no"])
    station = frappe.copy_doc(frappe.get_doc("Workstation", template.operations[0].workstation), ignore_no_copy=False)
    station.workstation_name = prefix + "-独立工位"
    station.insert()
    raw = frappe.get_doc({"doctype": "Item", "item_code": prefix + "-原料", "item_name": "本单边界样例原料",
        "item_group": frappe.get_cached_value("Item", template.items[0].item_code, "item_group"),
        "stock_uom": template.items[0].stock_uom, "is_stock_item": 1}).insert()
    finished = frappe.get_doc({"doctype": "Item", "item_code": prefix + "-成品", "item_name": "本单边界样例成品",
        "item_group": frappe.get_cached_value("Item", template.item, "item_group"), "stock_uom": template.uom, "is_stock_item": 1}).insert()
    bom = frappe.copy_doc(template, ignore_no_copy=False)
    bom.docstatus, bom.is_default, bom.item, bom.quantity = 0, 1, finished.name, 1
    bom.set("items", [])
    bom.append("items", {"item_code": raw.name, "qty": 0.5, "uom": raw.stock_uom, "stock_uom": raw.stock_uom,
        "conversion_factor": 1, "source_warehouse": old.source_warehouse})
    for row in bom.operations:
        row.workstation = station.name
    bom.insert().submit()
    warehouse = old.wip_warehouse
    if warehouse == old.source_warehouse:
        warehouse = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": prefix + "-在制仓", "company": old.company}).insert().name
    editor_role = frappe.get_doc({"doctype": "Role", "role_name": prefix + "-BOM维护", "desk_access": 1}).insert().name
    add_permission("BOM", editor_role, ptype="read")
    for right in ("create", "write"):
        update_permission_property("BOM", editor_role, 0, right, 1)
    warehouse_role = frappe.get_doc({"doctype": "Role", "role_name": prefix + "-仓管", "desk_access": 1}).insert().name
    for dt in ("Stock Entry", "Work Order", "Job Card", "Item", "Warehouse"):
        add_permission(dt, warehouse_role, ptype="read")
    for right in ("create", "write", "submit", "cancel"):
        update_permission_property("Stock Entry", warehouse_role, 0, right, 1)
    editor_roles = [r.role for r in frappe.get_doc("User", entries["actors"]["initiator"]["user"]).roles] + [editor_role]
    actors = {}
    for key, label, roles in (("editor", "本单用料维护员", editor_roles), ("warehouse", "本单领退仓管", [warehouse_role])):
        user = prefix.lower() + "-" + key + "@example.invalid"
        frappe.get_doc({"doctype": "User", "email": user, "first_name": label, "language": "zh", "time_zone": "Asia/Shanghai",
            "send_welcome_email": 0, "user_type": "System User", "roles": [{"role": role} for role in roles]}).insert()
        password = secrets.token_urlsafe(24)
        update_password(user, password)
        add_user_permission("Company", old.company, user)
        add_user_permission("Department", old.production_team, user, applicable_for="Work Order")
        if key == "warehouse":
            for wh in {warehouse, old.source_warehouse}:
                add_user_permission("Warehouse", wh, user)
        actors[key] = {"user": user, "password": password}
    # New raw material means its Bin/stock activity cannot rewrite old item balances.
    receipt = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "purpose": "Material Receipt",
        "company": old.company, "to_warehouse": old.source_warehouse, "items": [{"item_code": raw.name,
            "qty": 100, "uom": raw.stock_uom, "stock_uom": raw.stock_uom, "conversion_factor": 1,
            "t_warehouse": old.source_warehouse, "basic_rate": 2, "cost_center": frappe.get_cached_value("Company", old.company, "cost_center")}]})
    receipt.insert().submit()
    frappe.set_user(actors["editor"]["user"])
    order = frappe.get_doc({"doctype": "Work Order", "production_item": finished.name, "bom_no": bom.name,
        "company": old.company, "production_team": old.production_team, "qty": 10, "stock_uom": finished.stock_uom,
        "expected_delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 7), "planned_start_date": frappe.utils.now(),
        "source_warehouse": old.source_warehouse, "wip_warehouse": warehouse, "fg_warehouse": old.fg_warehouse}).insert()
    for row in bom.operations:
        order.append("operations", {"operation": row.operation, "workstation": station.name, "time_in_mins": row.time_in_mins, "sequence_id": row.sequence_id})
    order.set_required_items()
    order.save()
    assert len(order.required_items) == 1 and order.required_items[0].required_qty == 5
    value = {"site": source["site"], "base_url": source["base_url"], "actors": actors, "order": order.name,
        "bom": bom.name, "bom_row": bom.items[0].name, "raw_item": raw.name, "workstation": station.name,
        "reviewer": old.approval_reviewed_by, "director": entries["actors"]["director"]["user"], "seed_receipt": receipt.name}
    baseline.write_text(json.dumps(before, ensure_ascii=False, indent=2, default=str))
    access.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    frappe.db.commit()
    print(json.dumps({"old_tables_captured": len(before), "new_items": 2, "new_bom": 1, "independent_station": 1,
        "new_users": 2, "new_roles": 2, "prepared_draft": 1, "required_quantity": 5, "fixture_seed_receipt": 1, "secrets_printed": False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
