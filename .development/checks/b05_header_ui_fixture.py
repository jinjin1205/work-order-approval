"""Minimal new ordinary actor/data for header acceptance; preserve all prior rows."""
import hashlib
import json
import os
import secrets
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission
from frappe.utils.password import update_password
os.umask(0o077)
os.chdir("sites")
p=Path("/tmp/b08-private")
access=p/"b05-header-ui.json"
baseline=p/"b05-header-before.json"
assert not access.exists() and not baseline.exists(),"Keep existing run; never recreate"
source=json.loads((p/"fixture.json").read_text())
details=json.loads((p/"b05-details-ui.json").read_text())
frappe.init(site=source["site"])
frappe.connect()
try:
    assert source["site"]=="xgd-b08-http.localhost" and frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    tables=["Work Order","Work Order Item","Work Order Operation","Job Card","Job Card Time Log","Stock Entry","Stock Entry Detail","Stock Ledger Entry","Workflow Action","Version","Comment","BOM","BOM Item","BOM Operation","Item","UOM","User","Has Role","Role","Custom DocPerm","User Permission","Employee","Workstation"]
    before={}
    for dt in tables:
        columns=sorted(frappe.db.get_table_columns(dt))
        before[dt]={"columns":columns,"rows":{row.name:hashlib.sha256(json.dumps(dict(row),sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest() for row in frappe.get_all(dt,fields=columns,limit_page_length=0)}}
    original=frappe.get_doc("Work Order",source["order"])
    route_missing=frappe.get_doc("BOM",original.bom_no)
    assert not route_missing.operations,"Choose real existing no-route BOM; do not silently modify it"
    actor=frappe.get_doc("User",details["user"])
    roles=[row.role for row in actor.roles]
    assert "生产工单发起" in roles and not set(roles)&{"System Manager","Manufacturing Manager","生产工单签批"}
    prefix="B05-HEADER-"+frappe.generate_hash(length=8)
    user=prefix.lower()+"@example.invalid"
    frappe.get_doc({"doctype":"User","email":user,"first_name":"字段与提示验收员","language":"zh","send_welcome_email":0,"user_type":"System User","roles":[{"role":role} for role in roles]}).insert()
    password=secrets.token_urlsafe(24);update_password(user,password)
    add_user_permission("Company",original.company,user)
    add_user_permission("Department",original.production_team,user,applicable_for="Work Order")
    no_bom=frappe.get_doc({"doctype":"Item","item_code":prefix+"-无BOM产品","item_name":"无BOM产品样例","item_group":frappe.db.get_value("Item",details["production_item"],"item_group"),"stock_uom":original.stock_uom,"is_stock_item":1}).insert()
    bom=frappe.get_doc("BOM",details["bom_no"])
    frappe.set_user(user)
    prepared=frappe.get_doc({"doctype":"Work Order","production_item":details["production_item"],"bom_no":bom.name,"company":original.company,"production_team":original.production_team,"qty":10,"stock_uom":original.stock_uom,"planned_start_date":frappe.utils.now(),"transfer_material_against":bom.transfer_material_against,"source_warehouse":original.source_warehouse,"wip_warehouse":original.wip_warehouse,"fg_warehouse":original.fg_warehouse,
        "operations":[{"operation":row.operation,"workstation":row.workstation,"time_in_mins":row.time_in_mins,"sequence_id":row.sequence_id,"bom":bom.name} for row in bom.operations]})
    # Controlled setup only: create a ready draft so the new missing-delivery gate is reachable.
    prepared.set_required_items()
    prepared.insert()
    assert not prepared.expected_delivery_date and len(prepared.operations)==3 and len(prepared.required_items)==1
    value={"site":source["site"],"base_url":source["base_url"],"user":user,"password":password,"company":original.company,"production_team":original.production_team,"production_item":details["production_item"],"bom_no":bom.name,"no_bom_item":no_bom.name,"no_route_item":original.production_item,"no_route_bom":original.bom_no,"source_warehouse":original.source_warehouse,"wip_warehouse":original.wip_warehouse,"fg_warehouse":original.fg_warehouse,"prepared_order":prepared.name}
    baseline.write_text(json.dumps(before,ensure_ascii=False,indent=2))
    access.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    frappe.db.commit()
    print(json.dumps({"new_narrow_initiator":True,"new_user":1,"new_no_bom_item":1,"prepared_no_delivery_draft":1,"prepared_operations":3,"prepared_materials":1,"old_tables_captured":len(before),"confirmed_reports":0,"stock_entries":0,"secrets_printed":False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
