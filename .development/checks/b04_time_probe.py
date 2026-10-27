"""Characterize native time/metric fields on one rollback-only synthetic task."""
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
    from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderRequiredQuantity
    from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation

    order, raw, bom = TestWorkOrderRequiredQuantity().make_quantity_order(0.5, planned=10)
    station = make_workstation(workstation_name=raw.name+'-工时').name
    operation = frappe.get_doc({'doctype': 'Operation', '__newname': raw.name+'-工序'}).insert().name
    order.append('operations', {'operation': operation, 'workstation': station, 'time_in_mins': 1})
    order.insert()
    base = {'doctype': 'Job Card', 'work_order': order.name, 'company': order.company,
            'operation': operation, 'operation_id': order.operations[0].name,
            'workstation': station, 'wip_warehouse': order.wip_warehouse, 'for_quantity': 10}
    fields = [f.fieldname for f in frappe.get_meta('Job Card Time Log').fields]
    print(json.dumps({'kind': 'fixture', 'site': frappe.local.site, 'timezone': frappe.db.get_single_value('System Settings','time_zone'), 'time_log_fields': fields},ensure_ascii=False))
    cases = [
        ('T01_elapsed', '2026-10-20 09:00:00', '2026-10-20 17:00:00', 999999, 0),
        ('T02_cross_day', '2026-10-20 22:00:00', '2026-10-21 02:00:00', 0, 0),
        ('T08_reverse', '2026-10-20 10:00:00', '2026-10-20 09:00:00', 0, 0),
        ('open_forged_minutes', '2026-10-20 09:00:00', None, 999999, 0),
        ('end_without_start', None, '2099-10-20 10:00:00', 999999, 0),
        ('M01_native_loss', '2026-10-20 09:00:00', '2026-10-20 10:00:00', 0, 8),
    ]
    for index,(case,start,end,minutes,completed) in enumerate(cases):
        point='b04_time_'+str(index); frappe.db.savepoint(point)
        result={'case':case,'input':{'from':start,'to':end,'client_minutes':minutes,'completed_qty':completed}}
        try:
            doc=frappe.get_doc({**base,'time_logs':[{'from_time':start,'to_time':end,'time_in_mins':minutes,'completed_qty':completed}]}).insert().reload()
            result.update(saved=True,minutes=doc.time_logs[0].time_in_mins,total_minutes=doc.total_time_in_mins,
                          total_completed=doc.total_completed_qty,process_loss=doc.process_loss_qty,status=doc.status)
        except Exception as exc:
            result.update(saved=False,error_type=type(exc).__name__,message=str(exc))
        finally:
            frappe.db.rollback(save_point=point)
        print(json.dumps(result,ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
