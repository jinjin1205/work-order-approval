"""Finite B04 native characterization. Synthetic rows roll back; never run Q05."""
import hashlib
import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import frappe
import erpnext

os.chdir('sites')
frappe.init(site='xgd-test.localhost')
frappe.connect()
try:
    assert frappe.conf.get('allow_tests')
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'})
    frappe.set_user('Administrator')
    frappe.flags.in_test = True
    from erpnext.manufacturing.doctype.work_order.test_work_order import (
        TestWorkOrderRequiredQuantity, make_bom, make_item,
        make_wo_order_test_record, test_stock_entry,
    )
    from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
    from frappe.utils.nestedset import get_root_of

    def text_value(dt, name, field):
        # Identifiers are only the hard-coded developer values below, never input.
        return frappe.db.sql(f'SELECT CAST(`{field}` AS CHAR) FROM `tab{dt}` WHERE name=%s', name)[0][0]

    def numeric(value):
        return {'text': str(value), 'type': type(value).__name__}

    def final(value):
        return str(value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))

    result = {'site': frappe.local.site, 'erpnext': erpnext.__version__, 'frappe': frappe.__version__,
              'mode': 'native characterization; rollback; no Q05', 'source_sha256': {}}
    for root, relative in [(Path(erpnext.__file__).parent, 'manufacturing/doctype/bom/bom.py'),
                           (Path(frappe.__file__).parent, 'database/mariadb/database.py'),
                           (Path(frappe.__file__).parent, 'model/base_document.py')]:
        result['source_sha256'][str(root / relative)] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    result['original_float_precision'] = frappe.db.get_single_value('System Settings', 'float_precision')
    if '--configured' in sys.argv:
        settings = frappe.get_single('System Settings')
        settings.float_precision = '6'
        settings.save()
        frappe.clear_cache()
    result['effective_float_precision'] = frappe.db.get_default('float_precision')

    helper = TestWorkOrderRequiredQuantity()
    order, raw, bom = helper.make_quantity_order(0.123456, planned=7, parent_qty=2)
    order.insert()
    bom.reload()
    order.reload()
    entry = test_stock_entry.make_stock_entry(item_code=raw.name, company=order.company,
        target=order.source_warehouse, qty=0.123456, basic_rate=2)
    entry.reload()
    sle = frappe.get_all('Stock Ledger Entry', filters={'voucher_no': entry.name}, fields=['name', 'actual_qty'])[0]
    result['six_places'] = {
        'input': '0.123456', 'bom_qty': numeric(bom.items[0].qty),
        'bom_qty_db': text_value('BOM Item', bom.items[0].name, 'qty'),
        'bom_stock_qty': numeric(bom.items[0].stock_qty),
        'planned': 7, 'parent_base': 2, 'required_qty': numeric(order.required_items[0].required_qty),
        'required_expected': final(Decimal('7') * Decimal('0.123456') / Decimal('2')),
        'entry_qty': numeric(entry.items[0].qty), 'transfer_qty': numeric(entry.items[0].transfer_qty),
        'effective_transfer_precision': entry.precision('transfer_qty', entry.items[0]),
        'stock_ledger_qty': numeric(sle.actual_qty), 'stock_ledger_db': text_value('Stock Ledger Entry', sle.name, 'actual_qty'),
        'bin_qty': numeric(frappe.db.get_value('Bin', {'item_code': raw.name, 'warehouse': order.source_warehouse}, 'actual_qty')),
    }
    print(json.dumps({'stage': 'six_places', 'result': result['six_places']}, ensure_ascii=False), flush=True)
    if '--stock-only' in sys.argv:
        assert result['effective_float_precision'] == '6'
        assert entry.items[0].transfer_qty == 0.123456
        assert sle.actual_qty == 0.123456
        assert result['six_places']['bin_qty']['text'] == '0.123456'
        assert order.required_items[0].required_qty == 0.4321
        print(json.dumps({'completed': True, 'scope': 'six-place stock after persisted native configuration',
                          'result': result}, ensure_ascii=False, indent=2), flush=True)
        sys.exit(0)

    company = order.company
    prefix = 'B04-chain-' + frappe.generate_hash(length=8)
    sub = make_item(prefix + '-SUB', {'item_group': get_root_of('Item Group'), 'is_stock_item': 1, 'stock_uom': raw.stock_uom})
    product = make_item(prefix + '-FG', {'item_group': get_root_of('Item Group'), 'is_stock_item': 1, 'stock_uom': 'Nos'})
    args = dict(company=company, currency=frappe.get_cached_value('Company', company, 'default_currency'),
                source_warehouse=order.source_warehouse, with_operations=False, rate=2)
    child = make_bom(item=sub.name, quantity=1, raw_materials=[raw.name], rm_qty=0.083333, **args)
    parent = make_bom(item=product.name, quantity=1, raw_materials=[sub.name], rm_qty=0.000167, **args)
    parent.reload()
    assert parent.items[0].bom_no == child.name, 'Nested BOM must really be linked'
    chain = make_wo_order_test_record(item=product.name, bom_no=parent.name, qty=1000000, company=company,
        source_warehouse=order.source_warehouse, wip_warehouse=order.wip_warehouse,
        fg_warehouse=order.fg_warehouse, use_multi_level_bom=1, do_not_save=True)
    chain.insert()
    chain.reload()
    assert chain.required_items[0].item_code == raw.name, 'Must consume exploded raw material'
    expanded = parent.exploded_items[0]
    reference = Decimal('0.083333') * Decimal('0.000167')
    result['multi_level'] = {
        'child_qty': '0.083333', 'parent_qty': '0.000167', 'plan': 1000000,
        'exact_intermediate': str(reference), 'native_intermediate': numeric(expanded.stock_qty),
        'intermediate_db': text_value('BOM Explosion Item', expanded.name, 'stock_qty'),
        'provider_qty': numeric(get_bom_items_as_dict(parent.name, company, qty=1000000)[raw.name].qty),
        'required_qty': numeric(chain.required_items[0].required_qty),
        'reference_without_intermediate_rounding': final(reference * Decimal('1000000')),
    }
    print(json.dumps({'stage': 'multi_level', 'result': result['multi_level']}, ensure_ascii=False), flush=True)

    loss_order, loss_raw, loss_bom = helper.make_quantity_order(0.5, planned=100, parent_qty=2)
    loss_fields = {dt: [{'fieldname': f.fieldname, 'label': f.label, 'fieldtype': f.fieldtype}
                       for f in frappe.get_meta(dt).fields if 'loss' in f.fieldname or 'scrap' in f.fieldname]
                   for dt in ['BOM', 'BOM Item', 'BOM Explosion Item']}
    # Characterize the existing field with a fresh BOM. Never relabel it as material loss.
    loss_product = make_item(prefix + '-LOSS', {'item_group': get_root_of('Item Group'),
        'is_stock_item': 1, 'stock_uom': loss_raw.stock_uom})
    process = make_bom(item=loss_product.name, quantity=2, raw_materials=[loss_raw.name],
        rm_qty=0.5, do_not_save=True, **args)
    process.process_loss_percentage = 10
    process.insert().submit()
    process.reload()
    supplied = get_bom_items_as_dict(process.name, company, qty=100)[loss_raw.name].qty
    result['material_loss'] = {'fields': loss_fields, 'input': {'plan': 100, 'unit_qty': '0.5', 'parent_base': 2, 'loss_percent': 10},
        'native_without_loss': numeric(loss_order.required_items[0].required_qty),
        'process_loss_qty': numeric(process.process_loss_qty), 'native_with_process_loss': numeric(supplied),
        'required_material_loss_expected': '27.5000', 'material_loss_rate_field': frappe.get_meta('BOM Item').has_field('loss_rate')}
    print(json.dumps({'stage': 'material_loss', 'result': result['material_loss']}, ensure_ascii=False), flush=True)
    print(json.dumps({'completed': True, 'result': result}, ensure_ascii=False, indent=2), flush=True)
finally:
    frappe.db.rollback()
    frappe.clear_cache()
    frappe.destroy()
