import json, os
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
os.chdir('sites')
p=Path('/tmp/b08-private/fixture.json')
f=json.loads(p.read_text())
if 'http_order' in f:
    import sys
    assert sys.argv[1:] == ['--after-current-read-fix']
    f.setdefault('prior_http_samples',[]).append({k:f[k] for k in ['http_order','http_operation_id','http_forbidden']})
frappe.init(site=f['site']);frappe.connect()
try:
    assert frappe.conf.b08_http_only
    old=frappe.get_doc('Work Order', f['order'])
    actors=[old.approval_requested_by,old.approval_reviewed_by,old.modified_by]
    frappe.set_user(actors[0])
    order=frappe.copy_doc(old)
    order.workflow_state='草稿'
    order.approval_requested_by=order.approval_reviewed_by=order.approval_note=None
    order.insert()
    for actor,action in zip(actors,['送审','审核通过','签批通过']):
        frappe.set_user(actor)
        apply_production_approval(order.name,action,str(order.modified));order.reload()
    frappe.set_user('Administrator')
    add_user_permission('Work Order',order.name,f['user'])
    f.update(http_order=order.name,http_operation_id=order.operations[0].name,http_forbidden=order.operations[1].name)
    p.write_text(json.dumps(f,ensure_ascii=False,indent=2,default=str)+'\n')
    frappe.db.commit()
    print(json.dumps(dict(separate_http_order=True,ui_order_unchanged=True,plan=order.qty)))
finally:
    frappe.db.rollback();frappe.destroy()
