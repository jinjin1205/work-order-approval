"""Prepare isolated R02 masters; business transitions run through ordinary HTTP actors."""
import json
import os
import secrets
import sys
from pathlib import Path

import frappe
from frappe.permissions import add_permission, add_user_permission, update_permission_property
from frappe.utils.password import update_password
from b08_distinct_concurrency_fixture import capture_tables, compare_tables, preserved, write_private
from b10_issue_fixture import TABLES

P = Path('/tmp/b08-private/b17-core')
EXTRA = ['Report', 'Custom Role', 'Custom Field', 'Property Setter', 'Document Naming Rule', 'Document Naming Rule Condition']


def prepare():
    from erpnext.stock.doctype.item.test_item import create_item
    from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

    assert not (P / 'access.json').exists(), 'No completed fixture replay'
    if (P / 'before.json').exists():
        before = json.loads((P/'before.json').read_text())
        assert preserved(compare_tables(before)), 'Previous failed setup must have rolled back'
    else:
        before = capture_tables(TABLES + EXTRA)
        write_private(P / 'before.json', before)
    entries = json.loads(Path('/tmp/b08-private/b05-entries-ui.json').read_text())
    details = json.loads(Path('/tmp/b08-private/b05-details-ui.json').read_text())
    query = json.loads(Path('/tmp/b08-private/b16-query/access.json').read_text())
    old = frappe.get_doc('Work Order', entries['copy_source'])
    bom_source = frappe.get_doc('BOM', details['bom_no'])
    prefix = 'b17-core-' + frappe.generate_hash(length=8)
    a = dict(site=frappe.local.site, base_url='http://127.0.0.1:18090', prefix=prefix,
             company=old.company, team=old.production_team, actors={}, warehouses={})
    for kind in ('source', 'wip', 'fg'):
        a['warehouses'][kind] = frappe.get_doc(dict(doctype='Warehouse', warehouse_name=prefix+'-'+kind,
                                                  company=old.company)).insert().name
    warehouse_role = frappe.get_doc(dict(doctype='Role', role_name=prefix+'-仓管', desk_access=1)).insert().name
    for dt in ('Stock Entry', 'Work Order', 'Job Card', 'Item', 'Warehouse', 'Stock Settings'):
        add_permission(dt, warehouse_role, ptype='read')
    for dt in ('Company', 'BOM', 'UOM', 'Stock Entry Type', 'Account', 'Cost Center', 'Item Group'):
        add_permission(dt, warehouse_role, ptype='select')
    for permission in ('create', 'write', 'submit', 'cancel'):
        update_permission_property('Stock Entry', warehouse_role, 0, permission, 1)
    correction_role = frappe.get_doc(dict(doctype='Role', role_name=prefix+'-更正', desk_access=1)).insert().name
    add_permission('Job Card', correction_role, ptype='read')
    update_permission_property('Job Card', correction_role, 0, 'cancel', 1)
    roles = {
        'planner': [r.role for r in frappe.get_doc('User', entries['actors']['initiator']['user']).roles],
        'reviewer': [r.role for r in frappe.get_doc('User', old.approval_reviewed_by).roles],
        'director': [r.role for r in frappe.get_doc('User', entries['actors']['director']['user']).roles],
        'worker': ['生产报工', query['roles']['read'], correction_role],
        'warehouse': [warehouse_role],
        'query': [query['roles']['export']],
    }
    for alias, assigned in roles.items():
        assert not set(assigned) & {'System Manager', 'Administrator'}
        user = frappe.get_doc(dict(doctype='User', email=prefix+'-'+alias+'@example.invalid',
            first_name='闭环验收'+alias, language='zh', send_welcome_email=0, user_type='System User',
            roles=[{'role': role} for role in assigned])).insert()
        password = secrets.token_urlsafe(24)
        update_password(user.name, password)
        user.reload(); user.api_key = frappe.generate_hash(length=15); user.api_secret = frappe.generate_hash(length=32); user.save()
        a['actors'][alias] = dict(user=user.name, password=password, api_key=user.api_key, api_secret=user.get_password('api_secret'))
        add_user_permission('Company', old.company, user.name)
        add_user_permission('Department', old.production_team, user.name, applicable_for='Work Order')
        for warehouse in a['warehouses'].values():
            add_user_permission('Warehouse', warehouse, user.name)
    frappe.get_doc(dict(doctype='Employee', first_name='闭环操作工', gender='Male', date_of_birth='1990-01-01',
        date_of_joining='2020-01-01', company=old.company, department=old.production_team,
        status='Active', user_id=a['actors']['worker']['user'], create_user_permission=0)).insert()
    raw = create_item(prefix+'-raw', company=old.company, warehouse=a['warehouses']['source'], stock_uom=details['unit'])
    raw.valuation_method = 'Moving Average'; raw.save()
    fg = create_item(prefix+'-fg', company=old.company, warehouse=a['warehouses']['fg'])
    station = frappe.copy_doc(frappe.get_doc('Workstation', bom_source.operations[0].workstation))
    station.workstation_name = prefix+'-station'; station.status = 'Off'; station.insert()
    bom = frappe.copy_doc(bom_source); bom.docstatus = 0; bom.item = fg.name; bom.quantity = 1
    bom.set('items', [dict(item_code=raw.name, qty=0.5, uom=raw.stock_uom, stock_uom=raw.stock_uom,
        conversion_factor=1, source_warehouse=a['warehouses']['source'], rate=3)])
    for row in bom.operations:
        row.workstation = station.name
    bom.insert().submit()
    assert len(bom.operations) == 3
    opening = [make_stock_entry(item_code=raw.name, company=old.company, target=a['warehouses']['source'],
                              qty=10, basic_rate=rate).name for rate in (2, 4)]
    a.update(raw=raw.name, fg=fg.name, bom=bom.name, unit=fg.stock_uom, station=station.name, opening=opening)
    assert preserved(compare_tables(before))
    write_private(P / 'access.json', a)
    frappe.db.commit()
    return {'masters_prepared': True, 'ordinary_actors': list(roles), 'business_orders': 0, 'old_tables_unchanged': len(before)}


def bind_order(name):
    a = json.loads((P/'access.json').read_text())
    order = frappe.get_doc('Work Order', name)
    assert order.production_item == a['fg'] and order.approval_requested_by == a['actors']['planner']['user']
    if 'order' in a:
        assert order.previous_work_order==a['order'] and frappe.db.get_value('Work Order',a['order'],'status')=='Stopped'
        a['previous_order']=a['order'];a['stage_prefix']='continuation-'
    for alias,actor in a['actors'].items():
        if alias=='planner':
            continue
        add_user_permission('Work Order', name, actor['user'])
    a['order'] = name
    (P/'access.json').write_text(json.dumps(a, ensure_ascii=False, indent=2))
    assert preserved(compare_tables(json.loads((P/'before.json').read_text())))
    frappe.db.commit()
    return {'bound_order': name, 'old_rows_unchanged': True}


def allow_planner_continuation():
    a=json.loads((P/'access.json').read_text())
    assert frappe.db.get_value('Work Order',a['order'],'status')=='Stopped'
    user=a['actors']['planner']['user']
    permission=frappe.db.get_value('User Permission',{'user':user,'allow':'Work Order','for_value':a['order']})
    assert permission and user.startswith(a['prefix'])
    frappe.delete_doc('User Permission',permission)
    assert preserved(compare_tables(json.loads((P/'before.json').read_text())))
    frappe.db.commit()
    return {'new_planner_retains_company_team_scope':True,'removed_test_only_order_restriction':1}


def audit():
    a = json.loads((P/'access.json').read_text())
    checks = compare_tables(json.loads((P/'before.json').read_text()))
    assert preserved(checks), checks
    result = dict(old_rows_unchanged=True, retention=checks, bins={}, configuration={
        key: frappe.db.get_single_value('Manufacturing Settings', key) for key in
        ('backflush_raw_materials_based_on', 'material_consumption', 'disable_capacity_planning')})
    result['configuration']['stock_workflows'] = frappe.db.count('Workflow', {'document_type':'Stock Entry','is_active':1})
    for kind, warehouse in a['warehouses'].items():
        item = a['fg'] if kind == 'fg' else a['raw']
        result['bins'][kind] = frappe.db.get_value('Bin', {'item_code':item, 'warehouse':warehouse},
                                                  ['actual_qty', 'stock_value'], as_dict=True)
    if 'order' in a:
        order = frappe.get_doc('Work Order', a['order'])
        result['order'] = order.as_dict()
        result['reports'] = frappe.get_all('Job Card', filters={'work_order':order.name, 'report_request_id':['is','set']},
            fields=['name','docstatus','operation_id','total_completed_qty','process_loss_qty','amended_from','correction_reason'])
        result['stock'] = frappe.get_all('Stock Entry', filters={'work_order':order.name},
            fields=['name','docstatus','purpose','is_return','fg_completed_qty','process_loss_qty'])
    return result


if __name__ == '__main__':
    os.umask(0o077); P.mkdir(mode=0o700, exist_ok=True)
    os.chdir('sites'); frappe.init(site='xgd-b08-http.localhost'); frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator'); frappe.flags.skip_test_records = True
        mode = sys.argv[1]
        assert mode in ('prepare', 'bind', 'audit','allow-continuation')
        result = prepare() if mode == 'prepare' else bind_order(sys.argv[2]) if mode == 'bind' else allow_planner_continuation() if mode=='allow-continuation' else audit()
        print(json.dumps(result, ensure_ascii=False, default=str))
    finally:
        frappe.db.rollback(); frappe.destroy()
