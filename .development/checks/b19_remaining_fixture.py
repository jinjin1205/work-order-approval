"""Reuse new isolated masters; old B19/B17 business rows remain untouched."""
import json
import os
import sys
import secrets
from pathlib import Path

import frappe
import b17_core_fixture as base
from b08_distinct_concurrency_fixture import compare_tables, preserved

P = Path('/tmp/b08-private/b19-remaining')
base.P = P


def audit():
    a = json.loads((P/'access.json').read_text())
    retention = compare_tables(json.loads((P/'before.json').read_text()))
    assert preserved(retention), retention
    orders = frappe.get_all('Work Order', filters={'production_item':a['fg']},
        fields=['name','docstatus','workflow_state','status','qty','expected_delivery_date','approval_requested_by',
                'approval_reviewed_by','approval_note','amended_from','previous_work_order','modified'])
    result = {'old_rows_unchanged':True,'retention':retention,'orders':orders,
              'site':frappe.local.site,'source_item':a['fg']}
    names = [row.name for row in orders]
    result['reports'] = frappe.get_all('Job Card', filters={'work_order':['in',names],'report_request_id':['is','set']},
        fields=['name','work_order','docstatus','total_completed_qty','process_loss_qty']) if names else []
    result['stock'] = frappe.get_all('Stock Entry', filters={'work_order':['in',names]},
        fields=['name','work_order','docstatus','purpose','is_return']) if names else []
    result['comments'] = frappe.get_all('Comment', filters={'reference_doctype':'Work Order','reference_name':['in',names],
        'comment_type':'Comment'}, fields=['name','reference_name','content','owner','creation']) if names else []
    result['versions'] = frappe.get_all('Version', filters={'ref_doctype':'Work Order','docname':['in',names]},
        fields=['name','docname','data','owner','creation']) if names else []
    return result


def rotate_reviewer_login():
    from frappe.utils.password import update_password
    a=json.loads((P/'access.json').read_text())
    user=a['actors']['reviewer']['user']
    assert user.startswith(a['prefix'])
    password=secrets.token_urlsafe(24)
    update_password(user,password,logout_all_sessions=True)
    a['actors']['reviewer']['password']=password
    (P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
    frappe.db.commit()
    return {'new_test_reviewer_password_rotated':True,'credentials_printed':False}


def prepare_security():
    from frappe.permissions import add_permission, add_user_permission, update_permission_property
    from frappe.utils.password import update_password
    a=json.loads((P/'access.json').read_text())
    assert 'security_prepared' not in a,'Do not replay prepared security actors'
    other_companies=frappe.get_all('Company',filters={'name':['!=',a['company']]},pluck='name')
    assert other_companies,'Need an existing isolated comparison company'
    role=frappe.get_doc(dict(doctype='Role',role_name=a['prefix']+'-附件维护',desk_access=1)).insert().name
    add_permission('File',role,ptype='read')
    for permission in ('create','write','delete'):
        update_permission_property('File',role,0,permission,1)
    for alias in ('planner','reviewer'):
        frappe.get_doc('User',a['actors'][alias]['user']).add_roles(role)
    read_role=json.loads(Path('/tmp/b08-private/b16-query/access.json').read_text())['roles']['read']
    for alias,roles,company,team in [
        ('foreign_director',['生产工单签批',read_role],other_companies[0],None),
        ('revoked_reviewer',['生产工单审核',read_role],a['company'],a['team']),
    ]:
        user=frappe.get_doc(dict(doctype='User',email=a['prefix']+'-'+alias+'@example.invalid',
            first_name='剩余权限验收'+alias,language='zh',send_welcome_email=0,user_type='System User',
            roles=[{'role':x}for x in roles])).insert()
        password=secrets.token_urlsafe(24);update_password(user.name,password)
        user.reload();user.api_key=frappe.generate_hash(length=15);user.api_secret=frappe.generate_hash(length=32);user.save()
        a['actors'][alias]=dict(user=user.name,password=password,api_key=user.api_key,api_secret=user.get_password('api_secret'))
        add_user_permission('Company',company,user.name)
        if team:add_user_permission('Department',team,user.name,applicable_for='Work Order')
    a['security_prepared']=True;a['attachment_role']=role
    (P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
    assert preserved(compare_tables(json.loads((P/'before.json').read_text())))
    frappe.db.commit()
    return {'new_file_role':True,'new_security_actors':2,'foreign_company_available':True,'old_rows_unchanged':True}


def revoke_reviewer():
    a=json.loads((P/'access.json').read_text())
    user=a['actors']['revoked_reviewer']['user']
    name=frappe.db.get_value('File',{'file_name':a['prefix']+'-作业要求-v1.txt'},'attached_to_name')
    assert name
    frappe.set_user(user)
    assert frappe.has_permission('Work Order','read',doc=name) and '生产工单审核'in frappe.get_roles()
    frappe.set_user('Administrator')
    frappe.get_doc('User',user).remove_roles('生产工单审核')
    frappe.set_user(user)
    assert frappe.has_permission('Work Order','read',doc=name) and '生产工单审核'not in frappe.get_roles()
    frappe.set_user('Administrator')
    assert preserved(compare_tables(json.loads((P/'before.json').read_text())))
    frappe.db.commit()
    return {'new_test_reviewer_role_revoked':True,'read_positive_preserved':True,'old_rows_unchanged':True}


def revoke_owner_scope():
    a=json.loads((P/'access.json').read_text())
    user=a['actors']['planner']['user']
    permission=frappe.db.get_value('User Permission',{'user':user,'allow':'Company','for_value':a['company']})
    assert permission,'Do not replay the scope change'
    foreign=frappe.db.get_value('User Permission',{'user':a['actors']['foreign_director']['user'],'allow':'Company'},'for_value')
    doc=frappe.get_doc('User Permission',permission);doc.for_value=foreign;doc.save()
    target=frappe.db.get_value('File',{'file_name':a['prefix']+'-作业要求-v1.txt'},'attached_to_name')
    assert not frappe.has_permission('Work Order','read',doc=target,user=user)
    assert preserved(compare_tables(json.loads((P/'before.json').read_text())))
    frappe.db.commit()
    return {'new_owner_company_scope_changed':True,'parent_read_now_denied':True,'old_rows_unchanged':True}


if __name__=='__main__':
    os.umask(0o077); P.mkdir(mode=0o700,exist_ok=True)
    os.chdir('sites'); frappe.init(site='xgd-b08-http.localhost'); frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator'); frappe.flags.skip_test_records=True
        mode=sys.argv[1]; assert mode in ('prepare','audit','rotate-reviewer-login','prepare-security','revoke-reviewer','revoke-owner-scope')
        handlers={'prepare':base.prepare,'audit':audit,'rotate-reviewer-login':rotate_reviewer_login,'prepare-security':prepare_security,'revoke-reviewer':revoke_reviewer,'revoke-owner-scope':revoke_owner_scope}
        print(json.dumps(handlers[mode](),ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback(); frappe.destroy()
