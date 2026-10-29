"""Read/approve only the newly named B06 fixture; no old rows are changed."""
import json
import os
import sys
from pathlib import Path
import frappe
from frappe.tests.utils import change_settings
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval

os.chdir("sites")
a = json.loads(Path("/tmp/b08-private/b06-tasks-ui.json").read_text())
assert a["site"] == "xgd-b08-http.localhost" and a["actors"]["editor"]["user"].startswith("b06-task-")
frappe.init(site=a["site"])
frappe.connect()
try:
    assert frappe.conf.b08_http_only
    mode = sys.argv[1]
    if mode == "cache":
        frappe.clear_cache(doctype="Work Order")
        frappe.cache.hdel("doctype_form_meta", "Work Order")
        frappe.db.commit()
        print(json.dumps({"work_order_cache_cleared": True}))
    elif mode == "approve":
        order = frappe.get_doc("Work Order", a["order"])
        assert order.workflow_state == "待审核", "Do not replay approval"
        for actor, action in ((a["reviewer"], "审核通过"), (a["director"], "签批通过")):
            frappe.set_user(actor)
            with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
                apply_production_approval(order.name, action, str(order.reload().modified))
        frappe.db.commit()
        print(json.dumps({"new_fixture_approved": True, "plan_cards": frappe.db.count("Job Card", {"work_order": order.name, "docstatus": 0})}))
    else:
        assert mode == "state"
        frappe.set_user("Administrator")
        order = frappe.get_doc("Work Order", a["order"])
        print(json.dumps({"state": order.workflow_state, "status": order.status, "parent_plan": order.qty,
            "produced": order.produced_qty, "tasks": [{"name": r.name, "plan": r.report_plan_qty, "scope": r.report_scope,
                "good": r.completed_qty, "bad": r.process_loss_qty, "status": r.status} for r in order.operations],
            "reports": frappe.db.count("Job Card", {"work_order": order.name, "docstatus": 1}),
            "cards": frappe.db.count("Job Card", {"work_order": order.name}),
            "inventory": frappe.db.count("Stock Entry", {"work_order": order.name})}, ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
