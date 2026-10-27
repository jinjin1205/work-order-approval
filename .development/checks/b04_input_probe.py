"""Characterize only the B04 input/save boundaries on rollback-only synthetic data."""
import json
import os

import frappe

os.chdir('sites')
frappe.init(site='xgd-test.localhost')
frappe.connect()
try:
    assert frappe.conf.get('allow_tests')
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'})
    frappe.set_user('Administrator')
    frappe.flags.in_test = True
    from frappe.utils.nestedset import get_root_of
    from erpnext.manufacturing.doctype.work_order.test_work_order import (
        TestWorkOrderRequiredQuantity, make_item, make_bom, make_wo_order_test_record,
    )
    order, raw, _ = TestWorkOrderRequiredQuantity().make_quantity_order(0.5, 10, 2)
    finished = make_item(raw.name + '-input-FG', {'item_group': get_root_of('Item Group'),
        'stock_uom': raw.stock_uom, 'is_stock_item': 1})
    bom = make_bom(item=finished.name, company=order.company,
        currency=frappe.get_cached_value('Company', order.company, 'default_currency'),
        quantity=1, raw_materials=[raw.name], rm_qty=0.5, rate=2,
        source_warehouse=order.source_warehouse, with_operations=False)
    cases = [1.123456, '1.123456', 1.1234567, 0, -1, '不是数字', 'NaN', 'Infinity', False,
             '123456789012.123456', '1000000000000']
    for subject in ('bom_base', 'bom_item_qty', 'work_order_qty'):
        for value in cases:
            frappe.db.savepoint('b04_input_case')
            record = {'subject': subject, 'input': value, 'input_type': type(value).__name__}
            try:
                if subject == 'work_order_qty':
                    doc = make_wo_order_test_record(item=finished.name, bom_no=bom.name, qty=1,
                        company=order.company, stock_uom=raw.stock_uom, source_warehouse=order.source_warehouse,
                        wip_warehouse=order.wip_warehouse, fg_warehouse=order.fg_warehouse, do_not_save=True)
                    doc.qty = value
                else:
                    doc = frappe.copy_doc(bom)
                    if subject == 'bom_base':
                        doc.quantity = value
                    else:
                        doc.items[0].qty = value
                doc.insert()
                doc.reload()
                if subject == 'bom_base':
                    dt, name, field, actual = 'BOM', doc.name, 'quantity', doc.quantity
                elif subject == 'bom_item_qty':
                    dt, name, field, actual = 'BOM Item', doc.items[0].name, 'qty', doc.items[0].qty
                else:
                    dt, name, field, actual = 'Work Order', doc.name, 'qty', doc.qty
                stored = frappe.db.sql(f'SELECT CAST(`{field}` AS CHAR) FROM `tab{dt}` WHERE name=%s', name)[0][0]
                record.update(accepted=True, saved_text=stored, readback=str(actual), readback_type=type(actual).__name__)
            except Exception as exc:
                # A characterization probe records failures, not a production fallback.
                record.update(accepted=False, error_type=type(exc).__name__, message=str(exc))
            finally:
                frappe.db.rollback(save_point='b04_input_case')
                frappe.clear_cache()
            print(json.dumps(record, ensure_ascii=False), flush=True)
finally:
    frappe.db.rollback()
    frappe.clear_cache()
    frappe.destroy()
