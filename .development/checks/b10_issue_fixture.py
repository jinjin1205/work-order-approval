"""B10 isolated issue samples; native ledger only, no old-row mutation or replay."""
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
import frappe
from frappe.permissions import add_permission, add_user_permission, update_permission_property
from frappe.tests.utils import change_settings
from frappe.utils.password import update_password
from b08_distinct_concurrency_fixture import capture_tables, compare_tables, preserved, write_private

P = Path('/tmp/b08-private/b10-issue')
TABLES = ['Work Order','Work Order Item','Work Order Operation','Job Card','Job Card Time Log','Stock Entry','Stock Entry Detail','Stock Ledger Entry','Bin','GL Entry','Repost Item Valuation','Workflow Action','Version','Comment','BOM','BOM Item','BOM Operation','BOM Explosion Item','Item','Item Default','User','Has Role','Role','Custom DocPerm','User Permission','Employee','Workstation','Quality Inspection','Quality Inspection Reading','File','DocShare']

def runtime():
    root = Path('/home/frappe/frappe-bench/apps/erpnext')
    paths = json.loads(Path('/b01/b09-lifecycle-source-manifest.json').read_text())['files']
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in paths}

def setup(*, prefix_label="b10-issue-", cases=("ui", "race-red", "race-green"), prepare_issue_drafts=True):
    from erpnext.stock.doctype.item.test_item import create_item
    from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
    from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval, make_stock_entry as draft
    assert not (P/'access.json').exists() and not (P/'before.json').exists(), 'No setup replay'
    write_private(P/'before.json', capture_tables(TABLES))
    entries = json.loads(Path('/tmp/b08-private/b05-entries-ui.json').read_text())
    details = json.loads(Path('/tmp/b08-private/b05-details-ui.json').read_text())
    old = frappe.get_doc('Work Order', entries['copy_source'])
    base_bom = frappe.get_doc('BOM', details['bom_no'])
    prefix = prefix_label + frappe.generate_hash(length=8)
    a = {'site':frappe.local.site,'base_url':'http://127.0.0.1:18090','prefix':prefix,'company':old.company,'actors':{},'cases':{},'source':runtime()}
    wh = {}
    for kind in ('source','wip','fg'):
        wh[kind] = frappe.get_doc({'doctype':'Warehouse','warehouse_name':prefix+'-'+kind,'company':old.company}).insert().name
    a['warehouses'] = wh
    role = frappe.get_doc({'doctype':'Role','role_name':prefix+'-仓管','desk_access':1}).insert().name
    for dt in ('Stock Entry','Work Order','Job Card','Item','Warehouse','Stock Settings'):
        add_permission(dt,role,ptype='read')
    for dt in ('Company','BOM','UOM','Stock Entry Type','Account','Cost Center','Item Group'):
        add_permission(dt,role,ptype='select')
    for permission in ('create','write','submit','cancel'):
        update_permission_property('Stock Entry',role,0,permission,1)
    editor_roles = [r.role for r in frappe.get_doc('User',entries['actors']['initiator']['user']).roles]
    for alias, roles in (('editor',editor_roles),('A',[role]),('B',[role])):
        user = prefix+'-'+alias.lower()+'@example.invalid'
        doc = frappe.get_doc({'doctype':'User','email':user,'first_name':'领料验收'+alias,'language':'zh','send_welcome_email':0,'user_type':'System User','roles':[{'role':r} for r in roles]}).insert()
        password = secrets.token_urlsafe(24)
        update_password(user,password)
        doc.reload(); doc.api_key=frappe.generate_hash(length=15); doc.api_secret=frappe.generate_hash(length=32); doc.save()
        a['actors'][alias]={'user':user,'password':password,'api_key':doc.api_key,'api_secret':doc.get_password('api_secret')}
        add_user_permission('Company',old.company,user)
        add_user_permission('Department',old.production_team,user,applicable_for='Work Order')
        for warehouse in wh.values():
            add_user_permission('Warehouse',warehouse,user)
        assert 'System Manager' not in frappe.get_roles(user)
    for case in cases:
        raw = create_item(prefix+'-'+case+'-raw',company=old.company,warehouse=wh['source'])
        raw.valuation_method='Moving Average'; raw.save()
        fg = create_item(prefix+'-'+case+'-fg',company=old.company,warehouse=wh['fg'])
        station = frappe.copy_doc(frappe.get_doc('Workstation',base_bom.operations[0].workstation))
        station.workstation_name=prefix+'-'+case; station.status='Off'; station.insert()
        bom=frappe.copy_doc(base_bom); bom.docstatus=0; bom.item=fg.name; bom.quantity=1
        bom.set('items',[{'item_code':raw.name,'qty':1,'uom':raw.stock_uom,'stock_uom':raw.stock_uom,'conversion_factor':1,'source_warehouse':wh['source'],'rate':3}])
        for row in bom.operations:
            row.workstation=station.name
        bom.insert().submit()
        for rate in (2,4):
            make_stock_entry(item_code=raw.name,company=old.company,target=wh['source'],qty=10,basic_rate=rate)
        frappe.set_user(a['actors']['editor']['user'])
        order=frappe.get_doc({'doctype':'Work Order','production_item':fg.name,'bom_no':bom.name,'company':old.company,'production_team':old.production_team,'qty':10,'stock_uom':fg.stock_uom,'expected_delivery_date':frappe.utils.add_days(frappe.utils.nowdate(),7),'planned_start_date':frappe.utils.now(),'source_warehouse':wh['source'],'wip_warehouse':wh['wip'],'fg_warehouse':wh['fg']}).insert()
        for row in bom.operations:
            order.append('operations',{'operation':row.operation,'workstation':station.name,'time_in_mins':row.time_in_mins,'sequence_id':row.sequence_id,'report_scope':'ALL'})
        order.set_required_items(); order.save()
        for user, action in ((a['actors']['editor']['user'],'送审'),(old.approval_reviewed_by,'审核通过'),(entries['actors']['director']['user'],'签批通过')):
            frappe.set_user(user)
            with change_settings('Manufacturing Settings',{'disable_capacity_planning':1}):
                apply_production_approval(order.name,action,str(order.reload().modified))
        order.reload(); assert order.docstatus==1 and order.workflow_state=='已批准'
        frappe.set_user('Administrator')
        for alias in ('A','B'):
            add_user_permission('Work Order',order.name,a['actors'][alias]['user'])
        a['cases'][case]={'order':order.name,'raw':raw.name,'drafts':{}}
        if prepare_issue_drafts and case.startswith('race'):
            for alias in ('A','B'):
                frappe.set_user(a['actors'][alias]['user'])
                doc=frappe.get_doc(draft(order.name,'Material Transfer for Manufacture',qty=6)).insert()
                a['cases'][case]['drafts'][alias]=doc.name
        frappe.set_user('Administrator')
    for alias in ('A','B'):
        frappe.set_user(a['actors'][alias]['user'])
        assert not frappe.has_permission('Work Order','write',doc=a['cases']['ui']['order'])
        assert frappe.has_permission('Stock Entry','submit')
    frappe.set_user('Administrator')
    retention=compare_tables(json.loads((P/'before.json').read_text()))
    assert preserved(retention),'Old rows changed during setup'
    write_private(P/'access.json',a)
    frappe.db.commit()
    return {'setup':True,'cases':len(cases),'ordinary_warehouse_users':2,'old_tables':len(retention),'old_rows_unchanged':True,'source':runtime(),'credentials_printed':False}

def audit():
    a=json.loads((P/'access.json').read_text())
    retention=compare_tables(json.loads((P/'before.json').read_text()))
    result={'old_rows_unchanged':preserved(retention),'retention':retention,'source':runtime(),'cases':{},
        'manual_issue_configuration':{
            'backflush_raw_materials_based_on':frappe.db.get_single_value('Manufacturing Settings','backflush_raw_materials_based_on'),
            'material_consumption':frappe.db.get_single_value('Manufacturing Settings','material_consumption'),
            'active_stock_entry_workflows':frappe.db.count('Workflow',{'document_type':'Stock Entry','is_active':1}),
            'stock_allow_negative':frappe.db.get_single_value('Stock Settings','allow_negative_stock')}}
    for case,data in a['cases'].items():
        order=frappe.get_doc('Work Order',data['order'])
        result['cases'][case]={'plan':order.qty,'transferred':order.required_items[0].transferred_qty,'consumed':order.required_items[0].consumed_qty,'order_transferred':order.material_transferred_for_manufacturing,'skip_transfer':order.skip_transfer,'from_wip_warehouse':order.from_wip_warehouse,'transfer_material_against':order.transfer_material_against,'bins':{},'entries':[]}
        result['cases'][case]['report_facts']=frappe.db.count('Job Card',{'work_order':order.name,'report_request_id':['is','set']})
        for kind in ('source','wip'):
            row=frappe.db.get_value('Bin',{'item_code':data['raw'],'warehouse':a['warehouses'][kind]},['actual_qty','stock_value'],as_dict=True)
            result['cases'][case]['bins'][kind]=dict(row) if row else {'actual_qty':0,'stock_value':0}
        for se in frappe.get_all('Stock Entry',filters={'work_order':order.name},fields=['name','docstatus'],order_by='creation'):
            result['cases'][case]['entries'].append({'docstatus':se.docstatus,'sle':frappe.db.count('Stock Ledger Entry',{'voucher_no':se.name})})
    assert result['old_rows_unchanged']
    return result

if __name__=='__main__':
    os.umask(0o077); P.mkdir(mode=0o700,exist_ok=True); os.chdir('sites')
    frappe.init(site='xgd-b08-http.localhost'); frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator'); frappe.flags.skip_test_records=True
        mode=sys.argv[1]
        assert mode in ('setup','audit','ui-permission')
        if mode=='ui-permission':
            a=json.loads((P/'access.json').read_text())
            role=a['prefix']+'-仓管'
            assert role.startswith('b10-issue-')
            add_permission('Stock Settings',role,ptype='read')
            frappe.db.commit()
            print(json.dumps({'new_fixture_role_stock_settings_read':True,'old_roles_changed':False}))
        else:
            print(json.dumps(setup() if mode=='setup' else audit(),ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback(); frappe.destroy()
