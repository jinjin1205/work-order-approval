"""Read only: retained synthetic BOM and pre-existing business rows; no secrets in output."""
import json
import os
from decimal import Decimal
from pathlib import Path

import frappe

private = Path('/private/b04-bom-ui')
fixture = json.loads((private / 'access.json').read_text())
baseline = json.loads((private / 'baseline.json').read_text())
os.chdir('sites')
frappe.init(site=fixture['site'])
frappe.connect()
try:
    existing = {}
    for dt, rows in baseline.items():
        current = frappe.get_all(dt, filters={'name': ['in', [r['name'] for r in rows]]},
            fields=['*'], order_by='name') if rows else []
        same = json.loads(frappe.as_json(current)) == rows
        existing[dt] = {'count': len(rows), 'unchanged': same}
        assert same, 'Pre-existing business rows changed: ' + dt
    bom = frappe.get_doc('BOM', fixture['bom'])
    base = frappe.db.sql('SELECT CAST(quantity AS CHAR) FROM tabBOM WHERE name=%s', bom.name)[0][0]
    material = frappe.db.sql('SELECT CAST(qty AS CHAR) FROM `tabBOM Item` WHERE name=%s', bom.items[0].name)[0][0]
    assert Decimal(base) == Decimal('2.123456')
    assert Decimal(material) == Decimal('0.623456')
    assert bom.items[0].material_loss_percent == 20 and bom.items[0].amount == 1.5
    assert bom.modified_by == fixture['user'] and bom.docstatus == 0
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'})
    print(json.dumps({'site': frappe.local.site, 'ordinary_user_saved': True,
        'role': 'Manufacturing User', 'draft': True, 'base_sql': base, 'material_sql': material,
        'loss_percent': 20, 'rate': bom.items[0].rate, 'amount': bom.items[0].amount,
        'raw_material_cost': bom.raw_material_cost, 'workflow_enabled': False,
        'existing_business_rows': existing}, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
