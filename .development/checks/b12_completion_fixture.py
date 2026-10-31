"""B12 exclusive stock/report fixtures; reuse B10 old-row audit and native approvals."""
import json
import os
import sys
from pathlib import Path
import frappe
from frappe.permissions import add_permission, update_permission_property
import b10_issue_fixture as base
from b08_distinct_concurrency_fixture import write_private

P = Path('/tmp/b08-private/b12-completion')
base.P = P

def prepare():
    from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
    from erpnext.manufacturing.doctype.job_card.job_card import preview_production_report_time, confirm_production_report
    assert not (P/'prepared.json').exists(), 'No replay'
    setup = base.setup(prefix_label='b12-completion-', cases=('ui','race-mfg','race-correction','race-cancel'), prepare_issue_drafts=False)
    a = json.loads((P/'access.json').read_text())
    editor = a['actors']['editor']['user']
    frappe.get_doc('User',editor).add_roles('生产报工')
    role = a['prefix']+'-更正验收'
    frappe.get_doc({'doctype':'Role','role_name':role,'desk_access':1}).insert()
    add_permission('Job Card',role,ptype='read')
    update_permission_property('Job Card',role,0,'cancel',1)
    frappe.get_doc('User',editor).add_roles(role)
    order=frappe.get_doc('Work Order',a['cases']['ui']['order'])
    frappe.get_doc({'doctype':'Employee','first_name':'成品入库验收','gender':'Male','date_of_birth':'1990-01-01','date_of_joining':'2020-01-01','company':order.company,'department':order.production_team,'status':'Active','user_id':editor,'create_user_permission':0}).insert()
    for case,data in a['cases'].items():
        frappe.set_user(a['actors']['A']['user'])
        order=frappe.get_doc('Work Order',data['order'])
        data['issue']=frappe.get_doc(make_stock_entry(order.name,'Material Transfer for Manufacture',qty=10)).insert().submit().name
        frappe.set_user(editor)
        reports=[]
        for index,row in enumerate(order.operations):
            args=dict(work_order=order.name,operation_id=row.name,from_time=f'2026-10-31 {8+index:02}:00:00',to_time=f'2026-10-31 {9+index:02}:00:00')
            preview=preview_production_report_time(**args)
            reports.append(confirm_production_report(**args,request_id=frappe.generate_hash(length=32),good_quantity=8 if case=='ui' else 10,bad_quantity=2 if case=='ui' else 0,shutdown_seconds=0,overtime_seconds=0,context_fingerprint=preview['context_fingerprint'])['name'])
        data['reports']=reports
        data['report_before']={name:frappe.as_json(frappe.get_doc('Job Card',name).as_dict()) for name in reports}
        for actor in ('A','B') if case in ('race-mfg','race-cancel') else ('A',):
            frappe.set_user(a['actors'][actor]['user'])
            qty=6 if case=='race-mfg' else 7 if case=='race-cancel' and actor=='B' else 4
            data['drafts'][actor]=frappe.get_doc(make_stock_entry(order.name,'Manufacture',qty=qty)).insert().name
        if case=='race-cancel':
            frappe.set_user(a['actors']['A']['user'])
            frappe.get_doc('Stock Entry',data['drafts']['A']).submit()
    frappe.set_user('Administrator')
    (P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
    result=audit(); assert result['old_rows_unchanged']
    write_private(P/'prepared.json',{'setup':setup,'audit':result})
    frappe.db.commit()
    return {'prepared':True,'cases':list(a['cases']),'old_rows_unchanged':True,'new_reports':sum(len(v['reports']) for v in a['cases'].values()),'credentials_printed':False}

def prepare_cancel_green():
    from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
    a=json.loads((P/'access.json').read_text())
    assert 'race-cancel-green' not in a['cases'], 'No replay'
    data=dict(a['cases']['race-cancel']); data['drafts']={}
    for actor,qty in (('A',4),('B',7)):
        frappe.set_user(a['actors'][actor]['user'])
        data['drafts'][actor]=frappe.get_doc(make_stock_entry(data['order'],'Manufacture',qty=qty)).insert().name
    frappe.set_user(a['actors']['A']['user'])
    frappe.get_doc('Stock Entry',data['drafts']['A']).submit()
    a['cases']['race-cancel-green']=data
    (P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
    frappe.db.commit()
    return {'cancel_green_prepared':True,'original_failed_schedule_retained':True}

def audit():
    a=json.loads((P/'access.json').read_text()); result=base.audit()
    for case,data in a['cases'].items():
        order=frappe.get_doc('Work Order',data['order'])
        fg=frappe.db.get_value('Bin',{'item_code':order.production_item,'warehouse':order.fg_warehouse},['actual_qty','stock_value'],as_dict=True)
        result['cases'][case].update(produced=order.produced_qty,loss=order.process_loss_qty,fg=dict(fg) if fg else {'actual_qty':0,'stock_value':0},reports_unchanged=all(frappe.as_json(frappe.get_doc('Job Card',name).as_dict())==value for name,value in data.get('report_before',{}).items()))
    return result

if __name__=='__main__':
    os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True);os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator');frappe.flags.skip_test_records=True
        assert sys.argv[1] in ('prepare','audit','cancel-green')
        print(json.dumps(prepare() if sys.argv[1]=='prepare' else prepare_cancel_green() if sys.argv[1]=='cancel-green' else audit(),ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback();frappe.destroy()
