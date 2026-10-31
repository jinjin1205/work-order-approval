"""Create only new A01 masters/users; no inventory opening or replay of previous facts."""
import json
import os
import secrets
import sys
from pathlib import Path

import frappe
from frappe.permissions import add_permission, add_user_permission
from frappe.utils.password import update_password
from b08_distinct_concurrency_fixture import capture_tables, compare_tables, preserved, write_private
from b10_issue_fixture import TABLES

P=Path('/tmp/b08-private/a01-boundary')


def prepare():
    from erpnext.stock.doctype.item.test_item import create_item
    assert not (P/'access.json').exists(),'No completed fixture replay'
    old=json.loads(Path('/tmp/b08-private/b19-remaining/access.json').read_text())
    before=capture_tables(TABLES+['Report','Custom Role','Custom Field','Property Setter','Document Naming Rule','Document Naming Rule Condition'])
    write_private(P/'before.json',before)
    prefix='a01-'+frappe.generate_hash(length=8)
    a=dict(prefix=prefix,site=frappe.local.site,base_url='http://127.0.0.1:18090',company=old['company'],team=old['team'],actors={},warehouses={})
    role=frappe.get_doc(dict(doctype='Role',role_name=prefix+'-AI只读',desk_access=1)).insert().name
    add_permission('Work Order',role,ptype='read')
    for alias in ['planner','reviewer','director','worker','reader']:
        roles=[role] if alias=='reader' else [r.role for r in frappe.get_doc('User',old['actors'][alias]['user']).roles]
        user=frappe.get_doc(dict(doctype='User',email=prefix+'-'+alias+'@example.invalid',first_name='草稿验收'+alias,
            language='zh',send_welcome_email=0,user_type='System User',roles=[{'role':r}for r in roles])).insert()
        password=secrets.token_urlsafe(24);update_password(user.name,password)
        user.reload();user.api_key=frappe.generate_hash(length=15);user.api_secret=frappe.generate_hash(length=32);user.save()
        a['actors'][alias]=dict(user=user.name,password=password,api_key=user.api_key,api_secret=user.get_password('api_secret'))
        add_user_permission('Company',a['company'],user.name)
        if alias!='director':add_user_permission('Department',a['team'],user.name,applicable_for='Work Order')
    frappe.get_doc(dict(doctype='Employee',first_name='合成草稿操作工',gender='Male',date_of_birth='1990-01-01',date_of_joining='2020-01-01',
        company=a['company'],department=a['team'],status='Active',user_id=a['actors']['worker']['user'],create_user_permission=0)).insert()
    for kind in ['source','wip','fg']:
        a['warehouses'][kind]=frappe.get_doc(dict(doctype='Warehouse',warehouse_name=prefix+'-'+kind,company=a['company'])).insert().name
    old_bom=frappe.get_doc('BOM',old['bom'])
    raw=create_item(prefix+'-raw',company=a['company'],warehouse=a['warehouses']['source'],stock_uom=old_bom.items[0].stock_uom)
    fg=create_item(prefix+'-fg',company=a['company'],warehouse=a['warehouses']['fg'])
    station=frappe.copy_doc(frappe.get_doc('Workstation',old_bom.operations[0].workstation))
    station.workstation_name=prefix+'-station';station.status='Off';station.insert()
    bom=frappe.copy_doc(old_bom);bom.docstatus=0;bom.item=fg.name;bom.quantity=1
    bom.set('items',[dict(item_code=raw.name,qty=0.5,uom=raw.stock_uom,stock_uom=raw.stock_uom,conversion_factor=1,source_warehouse=a['warehouses']['source'])])
    for row in bom.operations:row.workstation=station.name
    bom.insert().submit()
    a.update(raw=raw.name,fg=fg.name,bom=bom.name,unit=fg.stock_uom)
    assert preserved(compare_tables(before))
    write_private(P/'access.json',a);frappe.db.commit()
    return dict(new_fixture=True,opening_stock_entries=0,old_rows_unchanged=True,credentials_printed=False)


def audit():
    a=json.loads((P/'access.json').read_text())
    retention=compare_tables(json.loads((P/'before.json').read_text()));assert preserved(retention),retention
    orders=frappe.get_all('Work Order',filters={'production_item':a['fg']},fields=['name','status','docstatus','workflow_state','modified'])
    names=[x.name for x in orders]
    reports=frappe.get_all('Job Card',filters={'work_order':['in',names],'report_request_id':['is','set']},
        fields=['name','owner','docstatus','report_request_id','total_completed_qty','process_loss_qty','report_time_context']) if names else []
    stock=frappe.get_all('Stock Entry',filters={'work_order':['in',names]},pluck='name')if names else []
    return dict(old_rows_unchanged=True,old_tables=len(retention),orders=orders,reports=reports,stock=stock)


if __name__=='__main__':
    os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True)
    os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator');frappe.flags.skip_test_records=True
        print(json.dumps({'prepare':prepare,'audit':audit}[sys.argv[1]](),ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback();frappe.destroy()
