"""B08 followup HTTP fixture; change only this run's new synthetic actor/configuration."""
import hashlib,json,os,sys
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission,remove_user_permission
from frappe.core.doctype.user.user import generate_keys
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
os.umask(0o077);os.chdir('sites')
p=Path('/tmp/b08-private/followup-http-20261028.json')
source=json.loads(Path('/tmp/b08-private/fixture.json').read_text())
frappe.init(site=source['site']);frappe.connect()
try:
    assert frappe.local.site=='xgd-b08-http.localhost' and frappe.conf.b08_http_only
    frappe.set_user('Administrator')
    mode=sys.argv[1]
    if mode=='setup':
        assert not p.exists(), 'Do not recreate/consume an existing HTTP followup'
        old=frappe.get_doc('Work Order',source['order'])
        prefix='b08-followup-'+frappe.generate_hash(length=8)
        user=prefix+'@example.invalid'
        frappe.get_doc({'doctype':'User','email':user,'first_name':'续接报工验收','send_welcome_email':0,'language':'zh','roles':[{'role':'生产报工'}]}).insert()
        employee=frappe.get_doc({'doctype':'Employee','first_name':'续接报工验收','gender':'Male','date_of_birth':'1990-01-01','date_of_joining':'2020-01-01','company':old.company,'department':old.production_team,'status':'Active','user_id':user,'create_user_permission':0}).insert()
        other=frappe.get_doc({'doctype':'Department','department_name':prefix+'-调岗','company':old.company}).insert()
        add_user_permission('Company',old.company,user)
        add_user_permission('Department',old.production_team,user,applicable_for='Work Order')
        actors=[old.approval_requested_by,old.approval_reviewed_by,source['user'].replace('-report@','-director@')]
        assert '生产工单签批' in frappe.get_roles(actors[2])
        frappe.set_user(actors[0])
        order=frappe.copy_doc(old);order.workflow_state='草稿'
        order.approval_requested_by=order.approval_reviewed_by=order.approval_note=None
        for row in order.operations:
            for field in ('completed_qty','process_loss_qty','actual_operation_time','actual_operating_cost'):row.set(field,0)
            row.actual_start_time=row.actual_end_time=None;row.status='Pending'
        order.operations[0].report_scope='DEPT';order.operations[0].report_employee=None
        order.operations[0].report_department=old.production_team
        order.insert()
        for actor,action in zip(actors,['送审','审核通过','签批通过']):
            frappe.set_user(actor);apply_production_approval(order.name,action,str(order.modified));order.reload()
        frappe.set_user('Administrator');add_user_permission('Work Order',order.name,user)
        f=dict(site=frappe.local.site,user=user,employee=employee.name,company=old.company,team=old.production_team,other=other.name,order=order.name,operation_id=order.operations[0].name,keys=generate_keys(user))
        p.write_text(json.dumps(f,ensure_ascii=False,indent=2));frappe.db.commit()
        print(json.dumps(dict(created_new_actor_and_order=True,scope='DEPT',no_existing_actor_changed=True)))
    else:
        f=json.loads(p.read_text());assert f['user'].startswith('b08-followup-')
        if mode=='move_department':
            e=frappe.get_doc('Employee',f['employee']);e.department=f['other'];e.save()
        elif mode=='revoke_company':remove_user_permission('Company',f['company'],f['user'])
        elif mode=='revoke_team':remove_user_permission('Department',f['team'],f['user'])
        elif mode=='restore':
            e=frappe.get_doc('Employee',f['employee']);e.department=f['team'];e.save()
            add_user_permission('Company',f['company'],f['user'])
            add_user_permission('Department',f['team'],f['user'],applicable_for='Work Order')
        elif mode=='state':
            cards=frappe.get_all('Job Card',filters={'work_order':f['order']},fields=['*'],order_by='name')
            rows=frappe.get_all('Job Card Time Log',filters={'parent':['in',[c.name for c in cards]]},fields=['*'],order_by='name')
            order=frappe.get_doc('Work Order',f['order'])
            state=dict(cards=cards,rows=rows,order=order.as_dict(),stock=frappe.db.count('Stock Entry'),ledger=frappe.db.count('Stock Ledger Entry'))
            print(json.dumps(dict(sha256=hashlib.sha256(frappe.as_json(state).encode()).hexdigest(),facts=sum(c.docstatus==1 and bool(c.report_request_id) for c in cards),good=order.operations[0].completed_qty)))
        else:raise ValueError(mode)
        if mode!='state':
            frappe.db.commit();print(json.dumps(dict(mode=mode,changed_new_synthetic_actor_only=True)))
finally:
    frappe.db.rollback();frappe.destroy()
