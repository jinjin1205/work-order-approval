"""Read-only verification of retained synthetic facts and the browser-approved example."""
import json
import os
from pathlib import Path
import frappe

os.chdir('sites')
frappe.init(site='xgd-b19-http.localhost')
frappe.connect()
try:
    assert frappe.conf.b19_http_only and frappe.conf.db_name == 'xgd_b19_http'
    frappe.set_user('Administrator')
    baseline = json.loads(Path('/evidence/B19/http/after-execution.json').read_text())
    checked = {}
    differences = []
    for key, doctype in [('work_order_rows', 'Work Order'), ('job_cards', 'Job Card'), ('stock_entries', 'Stock Entry')]:
        rows = baseline[key]
        for old in rows:
            # The baseline uses get_all rows. Compare database columns, not get_doc's virtual fields.
            current = json.loads(frappe.as_json(frappe.db.get_value(doctype, old['name'], list(old), as_dict=True)))
            for field, value in old.items():
                if not field.startswith('__'):
                    if current.get(field) != value:
                        differences.append({'doctype': doctype, 'field': field,
                            'database_matches_baseline': frappe.db.get_value(doctype, old['name'], field) == value,
                            'baseline_type': type(value).__name__, 'current_type': type(current.get(field)).__name__})
        checked[doctype] = len(rows)
    assert not differences, differences
    for old in baseline['legacy_tasks']:
        current = json.loads(frappe.as_json(frappe.get_doc('Job Card', old['name']).as_dict()))
        for field in ('docstatus', 'work_order', 'status', 'time_logs', 'total_time_in_mins', 'total_completed_qty'):
            assert current.get(field) == old.get(field), ('Legacy Job Card', field)
    access = json.loads(Path('/private/b19-http/ui-access.json').read_text())
    demo = frappe.get_doc('Work Order', access['draft_orders'][0])
    assert demo.docstatus == 1 and demo.workflow_state == '已批准' and demo.status == 'Not Started'
    cards = frappe.get_all('Job Card', filters={'work_order': demo.name}, fields=['name', 'docstatus', 'total_time_in_mins', 'total_completed_qty'])
    assert len(cards) == 3 and all(row.docstatus == 0 and row.total_time_in_mins == 0 and row.total_completed_qty == 0 for row in cards)
    assert not frappe.db.count('Job Card Time Log', {'parent': ['in', [row.name for row in cards]]})
    assert not frappe.db.count('Stock Entry', {'work_order': demo.name})
    comments = frappe.get_all('Comment', filters={'reference_doctype': 'Work Order', 'reference_name': demo.name, 'comment_type': 'Comment'}, pluck='content')
    assert all(any('审批动作：' + action in value for value in comments) for action in ('送审', '审核通过', '签批通过'))
    terminated = frappe.get_doc('Work Order', access['draft_orders'][1])
    assert terminated.workflow_state == '终止' and terminated.approval_note == '合成样例需求取消'
    print(json.dumps({'retained_http_database_fields_match': checked,
        'retained_legacy_tasks_match': len(baseline['legacy_tasks']),
        'demo': {'approval_state': demo.workflow_state, 'execution_state': demo.status, 'draft_tasks': len(cards),
            'time_logs': 0, 'stock_entries': 0, 'three_action_records_present': True},
        'second_draft_terminated_with_reason': True, 'read_only': True,
        'limit': 'Specific retained rows and demo facts; not all-table immutability or business acceptance'}, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
