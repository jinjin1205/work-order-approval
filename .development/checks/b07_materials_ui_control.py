"""Controlled native stock prerequisites on the newly isolated B07 order only."""
import json
import os
import sys
from pathlib import Path
import frappe
from frappe.tests.utils import change_settings
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval, make_stock_return_entry, get_production_material_summary

os.chdir("sites")
p = Path("/tmp/b08-private/b07-materials-ui.json")
a = json.loads(p.read_text())
assert a["site"] == "xgd-b08-http.localhost" and a["actors"]["editor"]["user"].startswith("b07-mat-")
frappe.init(site=a["site"])
frappe.connect()
try:
    assert frappe.conf.b08_http_only
    order = frappe.get_doc("Work Order", a["order"])
    mode = sys.argv[1]
    if mode == "roundtrip":
        assert order.workflow_state == "待审核" and not a.get("issue"), "Do not repeat stock/approval"
        for user, action in ((a["reviewer"], "审核通过"), (a["director"], "签批通过")):
            frappe.set_user(user)
            with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
                apply_production_approval(order.name, action, str(order.reload().modified))
        frappe.set_user(a["actors"]["warehouse"]["user"])
        row = order.required_items[0]
        entry = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Transfer for Manufacture",
            "purpose": "Material Transfer for Manufacture", "work_order": order.name, "company": order.company,
            "fg_completed_qty": order.qty, "from_warehouse": order.source_warehouse, "to_warehouse": order.wip_warehouse,
            "items": [{"item_code": row.item_code, "qty": row.required_qty, "uom": row.stock_uom,
                "stock_uom": row.stock_uom, "conversion_factor": 1, "s_warehouse": order.source_warehouse,
                "t_warehouse": order.wip_warehouse, "cost_center": frappe.get_cached_value("Company", order.company, "cost_center")}]})
        entry.insert().submit()
        returned = make_stock_return_entry(order.name)
        returned.company = order.company
        returned.items[0].cost_center = frappe.get_cached_value("Company", order.company, "cost_center")
        returned.submit()
        a.update(issue=entry.name, returned=returned.name)
        frappe.db.commit()
        p.write_text(json.dumps(a, ensure_ascii=False, indent=2))
        print(json.dumps({"native_issue": row.required_qty, "native_return": row.required_qty, "new_stock_documents": 2}))
    else:
        assert mode == "state"
        frappe.set_user(a["actors"]["editor"]["user"])
        result = get_production_material_summary(order.name)
        print(json.dumps({"workflow": order.workflow_state, "bom_source_quantity": frappe.db.get_value("BOM Item", a["bom_row"], "qty"),
            "product_bom_versions": frappe.get_all("BOM", filters={"item": order.production_item}, fields=["name", "docstatus"], order_by="creation"),
            "material_rows": result["items"], "can_write_bom": result["can_write_bom"],
            "order_produced": order.produced_qty}, ensure_ascii=False, default=str))
finally:
    frappe.db.rollback()
    frappe.destroy()
