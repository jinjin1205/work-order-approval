"""Prepare only approval metadata on the isolated test site; never activate a workflow."""
import hashlib
import json
import os
import sys
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

os.chdir('sites')
frappe.init(site='xgd-test.localhost')
frappe.connect()
try:
    assert frappe.conf.get('allow_tests'), 'Test site must allow tests'
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'}), 'Existing workflow requires review'
    frappe.set_user('Administrator')
    fields = [
        dict(fieldname='workflow_state', label='审批状态', fieldtype='Link', options='Workflow State', allow_on_submit=1, no_copy=1, read_only=1),
        dict(fieldname='production_team', label='执行班组', fieldtype='Link', options='Department'),
        dict(fieldname='approval_requested_by', label='发起人', fieldtype='Link', options='User', read_only=1, no_copy=1),
        dict(fieldname='approval_reviewed_by', label='审核人', fieldtype='Link', options='User', read_only=1, no_copy=1),
        dict(fieldname='approval_note', label='审批原因', fieldtype='Small Text', read_only=1, no_copy=1),
        dict(fieldname='previous_work_order', label='剩余需求来源工单', fieldtype='Link', options='Work Order', no_copy=1),
    ]
    def snapshot():
        result = {}
        for dt in ['Work Order', 'Work Order Item', 'Work Order Operation', 'Job Card', 'Job Card Time Log', 'Stock Entry', 'Stock Entry Detail', 'Stock Ledger Entry', 'Workflow Action', 'Version', 'Comment']:
            rows = frappe.get_all(dt, fields=['*'], order_by='name')
            if dt == 'Work Order':
                for row in rows:
                    for f in fields:
                        row.pop(f['fieldname'], None)
            result[dt] = dict(count=len(rows), sha256=hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest())
        return result
    before = snapshot()
    if '--prepare' in sys.argv:
        create_custom_fields({'Work Order': fields}, update=False)
        frappe.db.commit()
    after = snapshot()
    assert before == after, 'Metadata preparation changed existing business data'
    approval_fields_empty = all(not row.get(f['fieldname']) for row in frappe.get_all('Work Order', fields=[f['fieldname'] for f in fields]) for f in fields)
    print(json.dumps(dict(approval_fields_empty=approval_fields_empty, site=frappe.local.site, mode='prepare' if '--prepare' in sys.argv else 'read', allow_tests=True, workflow_count=0, business_data=after, metadata_present=all(frappe.get_meta('Work Order').has_field(f['fieldname']) for f in fields)), ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
