"""B11 uses the B10 isolated fixture; only new return/consumption cases are prepared."""
import json
import os
import sys
from pathlib import Path
import frappe
from frappe.tests.utils import change_settings
import b10_issue_fixture as base
from b08_distinct_concurrency_fixture import write_private

P=Path('/tmp/b08-private/b11-return')
base.P=P

def returned(order, issue, quantity):
    doc=frappe.new_doc('Stock Entry')
    doc.update({'company':order.company,'purpose':'Material Transfer for Manufacture','work_order':order.name,'is_return':1})
    row=issue.items[0]
    doc.append('items',{'item_code':row.item_code,'qty':quantity,'uom':row.stock_uom,'stock_uom':row.stock_uom,'conversion_factor':1,'s_warehouse':row.t_warehouse,'t_warehouse':row.s_warehouse,'against_stock_entry':issue.name,'ste_detail':row.name,'cost_center':row.cost_center})
    doc.set_stock_entry_type()
    return doc

def prepare():
    from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
    from erpnext.manufacturing.doctype.job_card.job_card import preview_production_report_time, confirm_production_report
    assert not (P/'prepared.json').exists(),'No fixture replay'
    setup=base.setup(prefix_label='b11-return-',cases=('ui','race-return','race-consume','race-cancel'),prepare_issue_drafts=False)
    a=json.loads((P/'access.json').read_text())
    editor=a['actors']['editor']['user']
    frappe.get_doc('User',editor).add_roles('生产报工')
    order=frappe.get_doc('Work Order',a['cases']['race-consume']['order'])
    frappe.get_doc({'doctype':'Employee','first_name':'退耗竞争前置','gender':'Male','date_of_birth':'1990-01-01','date_of_joining':'2020-01-01','company':order.company,'department':order.production_team,'status':'Active','user_id':editor,'create_user_permission':0}).insert()
    for case,data in a['cases'].items():
        frappe.set_user(a['actors']['A']['user'])
        order=frappe.get_doc('Work Order',data['order'])
        issue=frappe.get_doc(make_stock_entry(order.name,'Material Transfer for Manufacture',qty=10)).insert().submit()
        data['issue']=issue.name
        if case in ('race-return','race-consume'):
            data['first_return']=returned(order,issue,2).insert().submit().name
        if case=='race-consume':
            frappe.set_user(editor)
            for index,row in enumerate(order.operations):
                args=dict(work_order=order.name,operation_id=row.name,from_time=f'2026-10-30 {8+index:02}:00:00',to_time=f'2026-10-30 {9+index:02}:00:00')
                preview=preview_production_report_time(**args)
                confirm_production_report(**args,request_id=frappe.generate_hash(length=32),good_quantity=10,bad_quantity=0,shutdown_seconds=0,overtime_seconds=0,context_fingerprint=preview['context_fingerprint'])
            frappe.set_user(a['actors']['B']['user'])
            consume=returned(order,issue,5)
            consume.purpose='Material Consumption for Manufacture';consume.is_return=0;consume.from_bom=1;consume.bom_no=order.bom_no;consume.fg_completed_qty=5
            consume.items[0].t_warehouse=None;consume.items[0].against_stock_entry=None;consume.items[0].ste_detail=None
            consume.set_stock_entry_type()
            with change_settings('Manufacturing Settings',{'material_consumption':1}):
                consume.insert()
            data['drafts']['B']=consume.name
        if case=='race-cancel':
            data['drafts']['A']=issue.name
        elif case!='ui':
            frappe.set_user(a['actors']['A']['user'])
            data['drafts']['A']=returned(order,issue,5).insert().name
        if case in ('race-return','race-cancel'):
            frappe.set_user(a['actors']['B']['user'])
            data['drafts']['B']=returned(order,issue,5).insert().name
    frappe.set_user('Administrator')
    (P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
    result=base.audit();assert result['old_rows_unchanged']
    write_private(P/'prepared.json',{'setup':setup,'audit':result})
    frappe.db.commit()
    return {'prepared':True,'cases':list(a['cases']),'old_rows_unchanged':True,'new_reports_for_consumption':3,'credentials_printed':False}

def prepare_remaining_race():
    # The earlier race exposed a settings-test collision. Keep its facts and add a new 2+2 case against remaining 3.
    a=json.loads((P/'access.json').read_text())
    assert 'race-return-remaining' not in a['cases'],'No replacement race replay'
    data=dict(a['cases']['race-return']);data['drafts']={}
    order=frappe.get_doc('Work Order',data['order'])
    assert order.required_items[0].transferred_qty-order.required_items[0].returned_qty==3
    for actor in ('A','B'):
        frappe.set_user(a['actors'][actor]['user'])
        data['drafts'][actor]=returned(order,frappe.get_doc('Stock Entry',data['issue']),2).insert().name
    a['cases']['race-return-remaining']=data
    (P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
    frappe.db.commit()
    return {'new_remaining_race_ready':True,'earlier_race_facts_retained':True}

def prepare_lock_race(case):
    assert case in ('lock-red','lock-green')
    a=json.loads((P/'access.json').read_text());assert case not in a['cases'],'No race fixture replay'
    data=dict(a['cases']['race-consume']);data['drafts']={'B':data['issue']}
    frappe.set_user(a['actors']['A']['user'])
    data['drafts']['A']=returned(frappe.get_doc('Work Order',data['order']),frappe.get_doc('Stock Entry',data['issue']),1).insert().name
    a['cases'][case]=data
    (P/'access.json').write_text(json.dumps(a,ensure_ascii=False,indent=2));frappe.db.commit()
    return {'lock_race_prepared':case}

def audit():
    a=json.loads((P/'access.json').read_text());result=base.audit()
    for case,data in a['cases'].items():
        order=frappe.get_doc('Work Order',data['order']);row=order.required_items[0]
        result['cases'][case]['returned']=row.returned_qty
        result['cases'][case]['net_issued']=row.transferred_qty-row.returned_qty
        result['cases'][case]['issue_status']=frappe.db.get_value('Stock Entry',data['issue'],'docstatus')
    return result

if __name__=='__main__':
    os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True);os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator');frappe.flags.skip_test_records=True
        mode=sys.argv[1];assert mode in ('prepare','audit','prepare-remaining-race','lock-red','lock-green')
        print(json.dumps(prepare() if mode=='prepare' else prepare_remaining_race() if mode=='prepare-remaining-race' else prepare_lock_race(mode) if mode.startswith('lock-') else audit(),ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback();frappe.destroy()
