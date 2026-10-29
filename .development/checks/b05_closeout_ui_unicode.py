"""One additional no-timer sample solely for the observed Chinese snapshot display fix."""
import json
import os
from pathlib import Path
import frappe
from frappe.tests.utils import change_settings
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
os.umask(0o077)
os.chdir("sites")
p=Path("/tmp/b08-private/b05-closeout-ui.json")
a=json.loads(p.read_text())
assert len(a["samples"])==3 and not any(s["mode"]=="unicode" for s in a["samples"])
frappe.init(site=a["site"])
frappe.connect()
try:
    assert frappe.conf.b08_http_only
    old=frappe.get_doc("Work Order",a["samples"][0]["order"])
    assert old.status=="Closed"
    frappe.set_user(old.approval_requested_by)
    order=frappe.get_doc({"doctype":"Work Order","production_item":old.production_item,"bom_no":old.bom_no,"qty":10,"company":old.company,"stock_uom":old.stock_uom,"production_team":old.production_team,"source_warehouse":old.source_warehouse,"wip_warehouse":old.wip_warehouse,"fg_warehouse":old.fg_warehouse,
        "operations":[{"operation":row.operation,"workstation":row.workstation,"time_in_mins":1,"report_scope":"ALL"} for row in old.operations]}).insert()
    order.set_required_items()
    order.save()
    for actor,action in ((old.approval_requested_by,"送审"),(old.approval_reviewed_by,"审核通过"),(a["user"],"签批通过")):
        frappe.set_user(actor)
        with change_settings("Manufacturing Settings",{"disable_capacity_planning":1}):
            apply_production_approval(order.name,action,str(order.reload().modified))
    card=frappe.db.get_value("Job Card",{"work_order":order.name,"operation_id":order.operations[0].name,"docstatus":0},"name")
    a["samples"].append({"mode":"unicode","order":order.name,"card":card,"modified":str(order.reload().modified),"report":None})
    frappe.db.commit()
    p.write_text(json.dumps(a,ensure_ascii=False,indent=2))
    print(json.dumps({"extra_display_sample":1,"timer_rows":0,"confirmed_reports":0,"old_records_rewritten":0,"prior_samples_replayed":0}))
finally:
    frappe.db.rollback()
    frappe.destroy()
