"""Read-only isolated-site preservation and native UI audit verification."""
import hashlib
import json
import os
from pathlib import Path
import frappe
os.chdir('sites')
frappe.init(site='xgd-test.localhost')
frappe.connect()
try:
    assert frappe.conf.allow_tests
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'})
    baseline = json.loads(Path('/private/b14-ui/data-before.json').read_text())['business_data']
    actual = {}
    for dt in baseline:
        rows = frappe.get_all(dt, fields=['*'], order_by='name')
        if dt == 'Work Order':
            for row in rows:
                for key in ('workflow_state', 'production_team', 'approval_requested_by', 'approval_reviewed_by', 'approval_note', 'previous_work_order'):
                    row.pop(key, None)
        if dt == 'Version':
            rows = [r for r in rows if r.ref_doctype != 'Production Time Rule']
        if dt == 'Comment':
            access = json.loads(Path("/private/b14-ui/access.json").read_text())
            rows = [r for r in rows if r.reference_doctype != "Production Time Rule"
                and not (r.reference_doctype == "User" and r.reference_name == access["user"] and r.comment_type == "Shared")]
        actual[dt] = {'count': len(rows), 'sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()}
    assert actual == baseline
    rules = frappe.get_all('Production Time Rule', fields=['name', 'priority', 'owner'])
    assert len(rules) == 1 and rules[0].priority == 3
    versions = frappe.get_all('Version', filters={'ref_doctype': 'Production Time Rule', 'docname': rules[0].name}, fields=['data', 'owner'])
    assert any(['priority', '1', '2'] in json.loads(v.data).get('changed', []) and v.owner == rules[0].owner for v in versions)
    print(json.dumps({'old_business_tables_unchanged': len(actual), 'excluded_only_new_configuration_audit_and_fixture_user_share': True,
        'ui_saved_rule_count': 1, 'native_priority_version_1_to_2': True,
        'ui_final_priority': 3, 'workflow_activated': False, 'G1_G2_G3_closed': False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
