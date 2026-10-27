"""Bounded native F-RPT-01 probe; rollback all synthetic rows, no confirmation API."""
import json
import os
import frappe
os.chdir('sites')
frappe.init(site='xgd-test.localhost')
frappe.connect()
try:
    assert frappe.conf.allow_tests
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'})
    frappe.set_user('Administrator')
    from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderRequiredQuantity
    from erpnext.manufacturing.doctype.work_order.work_order import create_job_card
    from erpnext.manufacturing.doctype.job_card.test_job_card import make_workstation
    case = TestWorkOrderRequiredQuantity()
    order, raw, bom = case.make_quantity_order(0.5, planned=10)
    order.transfer_material_against = 'Work Order'
    order.skip_transfer = 1
    for i in range(3):
        operation = frappe.get_doc({'doctype': 'Operation', '__newname': raw.name + '-op' + str(i)}).insert().name
        station = make_workstation(workstation_name=raw.name + '-station' + str(i)).name
        order.append('operations', {'operation': operation, 'workstation': station, 'time_in_mins': 1})
    order.insert().submit()
    plans = frappe.get_all('Job Card', filters={'work_order': order.name}, fields=['name', 'for_quantity', 'operation_id', 'docstatus'])
    assert len(plans) == 3 and all(p.for_quantity == 10 and p.docstatus == 0 for p in plans)
    print(json.dumps({'case': 'minimum_fixture', 'runnable': True, 'plan_quantity': order.qty, 'operation_count': len(order.operations), 'native_plan_cards': len(plans), 'each_plan_card_quantity': 10, 'identity': 'Administrator preparation only', 'workflow_tested': False}))
    frappe.db.savepoint('before_extra_fact')
    row = order.operations[0]
    row.job_card_qty = 1
    card = create_job_card(order, row)
    try:
        card.insert()
    except frappe.ValidationError as exc:
        print(json.dumps({'case': 'first_separate_good_one', 'saved': False, 'exception': type(exc).__name__, 'message': str(exc), 'followup_facts': 'not executed because first fact rejected'}, ensure_ascii=False))
    else:
        print(json.dumps({'case': 'first_separate_good_one', 'saved': True}))
    finally:
        frappe.db.rollback(save_point='before_extra_fact')
    plan = frappe.get_doc('Job Card', next(p.name for p in plans if p.operation_id == row.name))
    plan.set('time_logs', [{'from_time': '2026-10-20 09:00:00', 'to_time': '2026-10-20 10:00:00', 'completed_qty': 1}])
    plan.save().reload()
    print(json.dumps({'case': 'one_good_on_native_plan', 'planned': plan.for_quantity, 'good': plan.total_completed_qty, 'native_process_loss': plan.process_loss_qty, 'expected_explicit_bad': 0, 'submitted': plan.docstatus == 1}, default=str))
    print(json.dumps({'case': 'scope', 'minimum_operator_parent_write': 'not reached', 'confirmation_snapshot': 'not implemented', 'G1_G2_G3': 'remain open'}))
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
    frappe.clear_cache()
    frappe.destroy()
