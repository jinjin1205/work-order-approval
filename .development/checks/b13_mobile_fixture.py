"""B13 ordinary roles, no Stock Settings grant; retain all prior 31-table rows."""
import json,os,sys
from pathlib import Path
import frappe
from frappe.permissions import update_permission_property
import b10_issue_fixture as base
from b08_distinct_concurrency_fixture import write_private
P=Path('/tmp/b08-private/b13-mobile');base.P=P

def prepare():
    assert not (P/'prepared.json').exists(),'No replay'
    setup=base.setup(prefix_label='b13-mobile-',cases=('ui','report-drop','report-offline'),prepare_issue_drafts=False)
    a=json.loads((P/'access.json').read_text());editor=a['actors']['editor']['user']
    update_permission_property('Stock Settings',a['prefix']+'-仓管',0,'read',0)
    frappe.get_doc('User',editor).add_roles('生产报工')
    order=frappe.get_doc('Work Order',a['cases']['ui']['order'])
    frappe.get_doc({'doctype':'Employee','first_name':'手机恢复验收','gender':'Male','date_of_birth':'1990-01-01','date_of_joining':'2020-01-01','company':order.company,'department':order.production_team,'status':'Active','user_id':editor,'create_user_permission':0}).insert()
    for data in a['cases'].values():
        data['plan_cards']=frappe.get_all('Job Card',filters={'work_order':data['order']},pluck='name')
    for alias in ('A','B'):
        frappe.set_user(a['actors'][alias]['user']);assert not frappe.has_permission('Stock Settings','read')
    frappe.set_user('Administrator');(P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
    result=base.audit();assert result['old_rows_unchanged'];write_private(P/'prepared.json',{'setup':setup,'audit':result});frappe.db.commit()
    return {'prepared':True,'cases':list(a['cases']),'old_rows_unchanged':True,'whole_stock_settings_read':False,'credentials_printed':False}

def audit():
    result=base.audit();a=json.loads((P/'access.json').read_text())
    for case,data in a['cases'].items():
        order=frappe.get_doc('Work Order',data['order']);result['cases'][case]['returned']=order.required_items[0].returned_qty
        result['cases'][case]['reports']=frappe.get_all('Job Card',filters={'work_order':order.name,'report_request_id':['is','set']},fields=['name','docstatus','report_request_id','total_completed_qty','process_loss_qty','operation_id'])
    return result

if __name__=='__main__':
    os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True);os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
    try:
        assert frappe.conf.b08_http_only;frappe.set_user('Administrator');frappe.flags.skip_test_records=True
        assert sys.argv[1] in ('prepare','audit')
        print(json.dumps(prepare() if sys.argv[1]=='prepare' else audit(),ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback();frappe.destroy()
