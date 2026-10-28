"""One new synthetic order on the retained B08 site; never consume old acceptance orders."""
import hashlib
import json
import os
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval

os.umask(0o077)
os.chdir('sites')
private=Path('/tmp/b08-private')
source=json.loads((private/'fixture.json').read_text())
target=private/'followup-20261028.json'
assert not target.exists(), 'Existing followup sample must be inspected, not recreated'
assert source['site']=='xgd-b08-http.localhost'
frappe.init(site=source['site']);frappe.connect()
try:
    assert frappe.conf.b08_http_only
    frappe.set_user('Administrator')
    tables=['Work Order','Work Order Item','Work Order Operation','Job Card','Job Card Time Log','Stock Entry','Stock Entry Detail','Stock Ledger Entry','Workflow Action','Version','Comment']
    baseline={dt:{r.name:hashlib.sha256(frappe.as_json(r).encode()).hexdigest() for r in frappe.get_all(dt,fields=['*'])} for dt in tables}
    (private/'followup-20261028-before.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2))
    old=frappe.get_doc('Work Order',source['order'])
    director=source['user'].replace('-report@','-director@')
    assert '生产工单签批' in frappe.get_roles(director)
    actors=[old.approval_requested_by,old.approval_reviewed_by,director]
    frappe.set_user(actors[0])
    order=frappe.copy_doc(old)
    order.workflow_state='草稿'
    order.approval_requested_by=order.approval_reviewed_by=order.approval_note=None
    for row in order.operations:
        for name in ('completed_qty','process_loss_qty','actual_operation_time','actual_operating_cost'):
            row.set(name,0)
        row.status='Pending'
        row.actual_start_time=row.actual_end_time=None
    order.insert()
    for actor,action in zip(actors,['送审','审核通过','签批通过']):
        frappe.set_user(actor)
        apply_production_approval(order.name,action,str(order.modified));order.reload()
    assert order.qty==10 and all(o.completed_qty==0 and o.process_loss_qty==0 for o in order.operations)
    frappe.set_user('Administrator')
    add_user_permission('Work Order',order.name,source['user'])
    value=dict(site=source['site'],order=order.name,operation_id=order.operations[0].name,user=source['user'],
        planned=10,scenario='合成样例：本笔实际开始由验收脚本准备时记时，结束由操作工在页面核对默认值')
    value['sample_started_at']=frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M:%S')
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    frappe.db.commit()
    print(json.dumps(dict(new_order=order.name,planned=10,ordinary_role=True,old_documents_preserved=True),ensure_ascii=False))
finally:
    frappe.db.rollback();frappe.destroy()
