"""Prepare new synthetic closing samples only; never alter prior actors or records."""
import hashlib
import json
import os
import secrets
from pathlib import Path
import frappe
from frappe.permissions import add_permission, add_user_permission
from frappe.utils.password import update_password
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
from erpnext.manufacturing.doctype.job_card.job_card import make_time_log, preview_production_report_time, confirm_production_report
os.umask(0o077)
os.chdir("sites")
p = Path("/tmp/b08-private")
access = p / "b05-closeout-ui.json"
baseline = p / "b05-closeout-before.json"
assert not access.exists() and not baseline.exists(), "Retain prior run; do not recreate samples"
source = json.loads((p / "fixture.json").read_text())
details = json.loads((p / "b05-details-ui.json").read_text())
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
        before[dt] = {"columns": columns, "rows": {row.name: hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest() for row in rows}}
    old = frappe.get_doc("Work Order", source["order"])
    signers = frappe.get_all("Comment", filters={"reference_doctype":"Work Order", "reference_name":old.name, "comment_type":"Comment", "content":["like","%审批动作：签批通过%"]}, pluck="owner")
    assert len(set(signers)) == 1
    director = frappe.get_doc("User", signers[0])
    prefix = "B05-END-" + frappe.generate_hash(length=8)
    role = frappe.get_doc({"doctype":"Role", "role_name":prefix+"-页面资料读取", "desk_access":1}).insert().name
    for dt in ("Item", "BOM", "Company", "Department", "Warehouse", "Operation", "Workstation", "UOM", "Employee"):
        add_permission(dt, role, ptype="read")
    add_permission("Project", role, ptype="select")
    def new_user(suffix, roles, label):
        name = prefix.lower()+suffix+"@example.invalid"
        frappe.get_doc({"doctype":"User", "email":name, "first_name":label,"language":"zh", "send_welcome_email":0,"user_type":"System User", "roles":[{"role":r} for r in roles]}).insert()
        password = secrets.token_urlsafe(24)
        update_password(name,password)
        add_user_permission("Company",old.company,name)
        add_user_permission("Department",old.production_team,name,applicable_for="Work Order")
        return name,password
    roles = [r.role for r in director.roles]+[role]
    assert "生产工单签批" in roles and not set(roles)&{"System Manager","Manufacturing Manager"}
    user,password = new_user("-director",roles,"人工结束验收厂长")
    worker,worker_password = new_user("-worker",[r.role for r in frappe.get_doc("User",source["user"]).roles],"结束差额样例报工员")
    assert "生产报工" in frappe.get_roles(worker)
    employee = frappe.get_doc({"doctype":"Employee","first_name":"结束差额样例报工员","gender":"Male","date_of_birth":"1990-01-01","date_of_joining":"2020-01-01","company":old.company,"department":old.production_team,"status":"Active","user_id":worker,"create_user_permission":0}).insert().name
    from frappe.tests.utils import change_settings
    workstation = frappe.get_doc({"doctype":"Workstation", "workstation_name":prefix+"-隔离工位", "production_capacity":1}).insert().name
    samples = []
    for mode in ("partial", "stopped", "race"):
        frappe.set_user(old.approval_requested_by)
        order = frappe.get_doc({"doctype":"Work Order", "production_item":details["production_item"], "bom_no":details["bom_no"], "qty":10, "company":old.company, "stock_uom":old.stock_uom, "production_team":old.production_team, "source_warehouse":old.source_warehouse, "wip_warehouse":old.wip_warehouse, "fg_warehouse":old.fg_warehouse,
            "operations":[{"operation":row.operation,"workstation":workstation,"time_in_mins":1,"report_scope":"PERSON" if i==0 else "ALL","report_employee":employee if i==0 else None} for i,row in enumerate(old.operations)]}).insert()
        # Existing fixture rows retain their manually prepared plan; material comes from original BOM entry.
        order.set_required_items()
        order.save()
        for actor, action in ((old.approval_requested_by,"送审"),(old.approval_reviewed_by,"审核通过"),(user,"签批通过")):
            frappe.set_user(actor)
            with change_settings("Manufacturing Settings", {"disable_capacity_planning":1}):
                apply_production_approval(order.name,action,str(order.reload().modified))
        order.reload()
        card = frappe.db.get_value("Job Card",{"work_order":order.name,"operation_id":order.operations[0].name,"docstatus":0},"name")
        if mode=="partial":
            frappe.set_user("Administrator")
            add_user_permission("Work Order",order.name,worker)
            frappe.set_user(worker)
            preview = preview_production_report_time(order.name,order.operations[0].name,"2026-10-20 07:00:00","2026-10-20 08:00:00")
            report = confirm_production_report(request_id=frappe.generate_hash(length=32),work_order=order.name,operation_id=order.operations[0].name,good_quantity=8,bad_quantity=2,from_time="2026-10-20 07:00:00",to_time="2026-10-20 08:00:00",shutdown_seconds=0,overtime_seconds=0,context_fingerprint=preview["context_fingerprint"])
        else:
            report = None
        if mode!="race":
            frappe.set_user(old.approval_requested_by)
            make_time_log({"job_card_id":card,"start_time":"2026-10-20 09:00:00" if mode=="partial" else "2026-10-20 11:00:00","status":"Work In Progress"})
        if mode=="stopped":
            frappe.set_user(user)
            apply_production_approval(order.name,"停止执行",str(order.reload().modified),"本包停止单收尾样例")
        samples.append({"mode":mode,"order":order.name,"card":card,"modified":str(order.reload().modified),"report":report["name"] if report else None})
    frappe.set_user("Administrator")
    from frappe.core.doctype.user.user import generate_keys
    secret = generate_keys(user)["api_secret"]
    key = frappe.db.get_value("User",user,"api_key")
    baseline.write_text(json.dumps(before,ensure_ascii=False,indent=2))
    access.write_text(json.dumps({"site":source["site"],"base_url":source["base_url"],"user":user,"password":password,"api_key":key,"api_secret":secret,"worker":worker,"worker_password":worker_password,"samples":samples},ensure_ascii=False,indent=2))
    frappe.db.commit()
    print(json.dumps({"new_factory_user":True,"new_narrow_worker":True,"new_orders":3,"partial_good":8,"partial_bad":2,"open_timers":2,"stopped_samples":1,"race_sample_prepared_without_timer":True,"old_tables_captured":len(before),"secrets_printed":False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
