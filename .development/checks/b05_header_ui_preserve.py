"""Read back prior rows and this package's two new UI orders; no mutations."""
import hashlib
import json
import os
from pathlib import Path
import frappe
os.chdir("sites")
p=Path("/tmp/b08-private")
a=json.loads((p/"b05-header-ui.json").read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    frappe.set_user("Administrator")
    before=json.loads((p/"b05-header-before.json").read_text())
    mismatch=[]; additions={}
    for dt,expected in before.items():
        rows=frappe.get_all(dt,fields=expected["columns"],limit_page_length=0)
        current={row.name:hashlib.sha256(json.dumps(dict(row),sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest() for row in rows}
        if any(current.get(name)!=digest for name,digest in expected["rows"].items()):mismatch.append(dt)
        additions[dt]=len(set(current)-set(expected["rows"]))
    assert not mismatch,mismatch
    orders=frappe.get_all("Work Order",filters={"owner":a["user"]},pluck="name")
    assert len(orders)==2 and additions["Work Order"]==2
    prepared=frappe.get_doc("Work Order",a["prepared_order"])
    assert prepared.workflow_state=="待审核" and prepared.docstatus==0
    assert str(prepared.expected_delivery_date)=="2026-11-05"
    assert len(prepared.operations)==3 and len(prepared.required_items)==1
    other=frappe.get_doc("Work Order",next(n for n in orders if n!=prepared.name))
    assert other.workflow_state=="草稿" and other.docstatus==0 and str(other.expected_delivery_date)=="2026-10-28"
    assert other.bom_no==a["no_route_bom"] and not other.operations and not other.required_items
    assert additions["Job Card"]==0 and additions["Job Card Time Log"]==0
    assert additions["Stock Entry"]==0 and additions["Stock Entry Detail"]==0 and additions["Stock Ledger Entry"]==0
    assert additions["User"]==1 and additions["Item"]==1
    print(json.dumps({"old_tables_preserved":len(before),"old_row_mismatches":0,"new_orders":2,"prepared_review_state":"待审核","prepared_due":"2026-11-05","prepared_plan_operations":3,"prepared_plan_materials":1,"new_page_draft_no_route":True,"no_route_operations":0,"no_route_materials":0,"blank_due_draft_earlier_verified":True,"overdue_delivery_preserved":"2026-10-28","distinct_native_numbers":len(set(orders))==2,"job_cards_added":0,"time_logs_added":0,"stock_entries_added":0,"stock_ledger_entries_added":0,"new_user":1,"new_item":1},ensure_ascii=False,indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
