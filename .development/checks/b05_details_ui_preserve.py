"""Bounded readback of retained rows and the one browser-created synthetic order."""
import hashlib
import json
import os
from pathlib import Path
import frappe
os.chdir("sites")
p = Path("/tmp/b08-private")
a = json.loads((p / "b05-details-ui.json").read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    frappe.set_user("Administrator")
    baseline=json.loads((p / "b05-details-before.json").read_text())
    mismatches=[]
    for dt, expected in baseline.items():
        rows=frappe.get_all(dt,fields=expected["columns"],limit_page_length=0)
        current={row.name:hashlib.sha256(json.dumps(dict(row),sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest() for row in rows}
        if any(current.get(name)!=digest for name,digest in expected["rows"].items()): mismatches.append(dt)
    assert not mismatches, mismatches
    orders=frappe.get_all("Work Order",filters={"owner":a["user"]},pluck="name")
    assert len(orders)==1
    order=frappe.get_doc("Work Order",orders[0])
    assert order.qty==10 and order.workflow_state=="草稿" and order.docstatus==0
    assert len(order.operations)==3 and len(order.required_items)==1 and order.required_items[0].required_qty==5
    assert order.bom_no==a["bom_no"]
    assert not frappe.db.exists("Job Card",{"work_order":order.name})
    assert not frappe.db.exists("Stock Entry",{"work_order":order.name})
    print(json.dumps({"old_tables_preserved":len(baseline),"old_row_mismatches":0,"new_browser_orders":1,"operations":3,"material_rows":1,"required_qty":5,"job_cards":0,"stock_entries":0,"draft_not_approved":True}))
finally:
    frappe.db.rollback()
    frappe.destroy()
