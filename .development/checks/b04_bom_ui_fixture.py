"""One retained synthetic BOM on the existing development site; no customer/site rebuild."""
import hashlib
import json
import os
from pathlib import Path
import secrets

import frappe

os.umask(0o077)
private = Path('/private/b04-bom-ui')
os.chdir('sites')
frappe.init(site='xgd-dev.localhost')
frappe.connect()
try:
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'})
    assert frappe.get_meta('BOM Item').has_field('material_loss_percent')
    if (private / 'access.json').exists():
        fixture = json.loads((private / 'access.json').read_text())
        assert frappe.db.exists('BOM', fixture['bom']) and frappe.db.exists('User', fixture['user'])
        print(json.dumps({'reused': True, 'site': frappe.local.site, 'no_new_records': True}))
    else:
        frappe.set_user('Administrator')
        from frappe.utils.nestedset import get_root_of
        from frappe.utils.password import update_password
        from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
        from erpnext.stock.doctype.item.test_item import make_item
        from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
        import erpnext

        baseline = {}
        for dt in ('BOM', 'BOM Item', 'Work Order', 'Job Card', 'Stock Entry', 'Stock Ledger Entry'):
            baseline[dt] = frappe.get_all(dt, fields=['*'], order_by='name')
        prefix = 'B04-中文样例-' + frappe.generate_hash(length=6)
        company = erpnext.get_default_company()
        unit = frappe.get_doc({'doctype': 'UOM', 'uom_name': prefix + '-单位', 'must_be_whole_number': 0}).insert().name
        warehouse = frappe.get_doc({'doctype': 'Warehouse', 'company': company, 'warehouse_name': prefix + '-原料仓'}).insert().name
        raw, finished = [make_item(prefix + '-' + suffix, {'item_group': get_root_of('Item Group'),
            'stock_uom': unit, 'is_stock_item': 1, 'valuation_method': 'Moving Average'}) for suffix in ('原料', '产品')]
        receipt = make_stock_entry(item_code=raw.name, company=company, target=warehouse, qty=40, basic_rate=2)
        bom = make_bom(item=finished.name, company=company, currency='CNY', quantity=2,
            raw_materials=[raw.name], rm_qty=0.5, rate=2, source_warehouse=warehouse, with_operations=False,
            do_not_save=True)
        bom.items[0].material_loss_percent = 10
        bom.insert()
        user = 'b04.bom@example.invalid'
        assert not frappe.db.exists('User', user), 'Existing unrelated user requires inspection'
        password = secrets.token_urlsafe(24)
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': '物料维护验收员', 'enabled': 1,
            'language': 'zh', 'time_zone': 'Asia/Shanghai', 'send_welcome_email': 0,
            'roles': [{'role': 'Manufacturing User'}]}).insert()
        update_password(user, password)
        fixture = {'site': frappe.local.site, 'base_url': 'http://xgd-dev.localhost:18086',
            'user': user, 'password': password, 'bom': bom.name, 'raw': raw.name, 'finished': finished.name,
            'warehouse': warehouse, 'receipt': receipt.name}
        frappe.db.commit()
        (private / 'baseline.json').write_text(frappe.as_json(baseline))
        (private / 'access.json').write_text(json.dumps(fixture, ensure_ascii=False, indent=2))
        print(json.dumps({'created': True, 'site': frappe.local.site, 'ordinary_role': 'Manufacturing User',
            'synthetic_bom_count': 1, 'synthetic_receipt_count': 1, 'workflow_enabled': False}, ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
