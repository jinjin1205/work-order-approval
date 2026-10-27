"""Verify native precision settings and identify their audit rows without exporting rows."""
import hashlib
import json
import os
import frappe

os.chdir('sites')
frappe.init(site='xgd-test.localhost')
frappe.connect()
try:
    settings = frappe.get_single('System Settings')
    rows = frappe.get_all('Version', fields=['*'], order_by='name')
    candidates = []
    for row in rows:
        if row.ref_doctype != 'System Settings':
            continue
        data = json.loads(row.data)
        if data.get('changed') != [['float_precision', '3', '6']]:
            continue
        remaining = [r for r in rows if r.name != row.name]
        candidates.append({'remaining_count': len(remaining), 'remaining_sha256': hashlib.sha256(
            json.dumps(remaining, sort_keys=True, default=str).encode()).hexdigest(),
            'changed_fields': ['float_precision'], 'old': '3', 'new': '6'})
    print(json.dumps({'site': frappe.local.site, 'setting': settings.float_precision,
        'effective_default': frappe.db.get_default('float_precision'), 'version_count': len(rows),
        'candidate_native_config_audits': candidates}, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
