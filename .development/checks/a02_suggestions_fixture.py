"""Reuse A01 master isolation without inventory setup or old business replay."""
import json
import os
import sys
from pathlib import Path
import frappe
import a01_boundary_fixture as base
from b08_distinct_concurrency_fixture import compare_tables, preserved, digest

P=Path('/tmp/b08-private/a02-suggestions')
base.P=P


def observe():
    a=json.loads((P/'access.json').read_text())
    before=json.loads((P/'before.json').read_text())
    retention=compare_tables(before)
    changed={}
    for doctype, result in retention.items():
        if result['changed']:
            changed[doctype]=[row.name for row in frappe.get_all(doctype,fields=before[doctype]['columns'],limit_page_length=0)
                if row.name in before[doctype]['rows'] and digest(dict(row))!=before[doctype]['rows'][row.name]]
    orders=frappe.get_all('Work Order',filters={'production_item':a['fg']},fields=['name','modified','status','docstatus'])
    names=[r.name for r in orders]
    return dict(old_rows_unchanged=preserved(retention),retention=retention,changed_old_ids=changed,
        orders=orders,plan_rows=frappe.get_all('Work Order Operation',filters={'parent':['in',names]},fields=['name','operation','report_plan_qty']),
        materials=frappe.get_all('Work Order Item',filters={'parent':['in',names]},fields=['name','required_qty','stock_uom']),
        reports=frappe.get_all('Job Card',filters={'work_order':['in',names]},pluck='name'),
        stock=frappe.get_all('Stock Entry',filters={'work_order':['in',names]},pluck='name'))

if __name__=='__main__':
    os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True)
    os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator');frappe.flags.skip_test_records=True
        print(json.dumps({'prepare':base.prepare,'audit':base.audit,'observe':observe}[sys.argv[1]](),ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback();frappe.destroy()
