"""Limited native-document observations; run once in the isolated bench console."""
import json
import traceback
from pathlib import Path
from datetime import datetime, timezone
import frappe
from frappe.utils import now, add_to_date
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_return_entry, make_stock_entry

output = Path('/home/frappe/frappe-bench/sites/r05-boundary-result-attempt3.json')
if output.exists() or frappe.local.site != 'r05.localhost':
    raise RuntimeError('Wrong site or existing output; do not overwrite evidence')
result = {'started_utc': datetime.now(timezone.utc).isoformat(), 'user': frappe.session.user,
          'scope': 'Native same-document resubmit, excess return, cancel/amend observations only', 'cases': []}
# Reuse the existing evaluation helpers, stopping before its execution guard.
helpers = {}
exec(Path('/eval/r02_probe.py').read_text().split('\nif OUTPUT.exists():', 1)[0], helpers)
helpers['PREFIX'] = 'R02-ERPNext-20261026-Y'
snapshot = helpers['snapshot']
old_settings = {key: frappe.db.get_single_value('Manufacturing Settings', key) for key in helpers['SETTINGS']}
try:
    frappe.db.set_single_value('Manufacturing Settings', helpers['SETTINGS'])
    frappe.db.commit()
    wo = frappe.get_doc('Work Order', '[本地样例编号已移除]')
    rm, fg = 'R02-ERPNext-20261026-B-C06-RM', 'R02-ERPNext-20261026-B-C06-FG'
    if wo.production_item != fg:
        raise RuntimeError('Expected committed CASE-06 fixture mismatch')
    entry = frappe.get_all('Stock Entry', filters={'work_order':wo.name,'docstatus':1,'is_return':0}, pluck='name')
    if len(entry) != 1:
        raise RuntimeError('Expected one effective transfer')
    for label, action in [
        ('CASE-06 return 9 after prior issue 10 and return 2', None),
    ]:
        c = {'case': label, 'before': snapshot(wo, rm, fg)}
        result['cases'].append(c)
        frappe.db.savepoint('boundary_case')
        try:
            if action:
                action()
            else:
                doc = make_stock_return_entry(wo.name)
                c['native_return_factory_observation'] = doc.as_dict()
                return_ids = frappe.get_all('Stock Entry', filters={'work_order':wo.name,'docstatus':1,'is_return':1}, pluck='name')
                if len(return_ids) != 1:
                    raise RuntimeError('Expected one committed return fixture')
                doc = frappe.copy_doc(frappe.get_doc('Stock Entry',return_ids[0]))
                doc.docstatus = 0
                c['input_method'] = 'Copy existing valid WIP-to-source return as new draft; choose qty 9; native factory has multiple rows recorded separately'
                if len(doc.items) != 1:
                    raise RuntimeError('Committed return fixture must have one row')
                doc.company = wo.company
                doc.items[0].cost_center = frappe.get_cached_value('Company',wo.company,'cost_center')
                doc.items[0].qty = 9
                c['submitted_input'] = doc.as_dict()
                doc.submit()
            c['outcome'] = 'returned_without_exception'
        except Exception as exc:
            c['outcome'] = 'exception'
            c['exception_class'] = type(exc).__name__
            c['exception_message'] = str(exc)
            c['traceback'] = traceback.format_exc()
        c['after_before_rollback'] = snapshot(wo,rm,fg)
        frappe.db.rollback(save_point='boundary_case')
        c['after_rollback'] = snapshot(wo,rm,fg)
        c['transaction'] = 'savepoint rolled back; original committed fixture retained'

    c = {'case':'CASE-05 cancel 10 and amend batch size to 8; keep work-order plan 10', 'steps':[]}
    result['cases'].append(c)
    try:
        wo, rm, fg = helpers['build_case'](c, 'C05', .5, 1)
        frappe.get_doc(make_stock_entry(wo.name,'Material Transfer for Manufacture',10)).submit()
        cards = frappe.get_all('Job Card', filters={'work_order':wo.name},pluck='name')
        if len(cards)!=1:
            raise RuntimeError('Expected one job card')
        card=frappe.get_doc('Job Card',cards[0])
        start=now()
        card.append('time_logs',{'from_time':start,'to_time':add_to_date(start,minutes=1),'completed_qty':10})
        card.remarks='Synthetic original report; cancellation reason: entered 10, actual 8'
        card.submit()
        c['original_before_cancel']=card.as_dict()
        card.cancel()
        c['original_after_cancel']=frappe.get_doc('Job Card',card.name).as_dict()
        amended=frappe.copy_doc(card)
        amended.amended_from=card.name
        amended.docstatus=0
        amended.for_quantity=8
        amended.time_logs[0].completed_qty=8
        amended.remarks='Synthetic correction from 10 to 8'
        amended.submit()
        c['amended']=frappe.get_doc('Job Card',amended.name).as_dict()
        c['final']=snapshot(wo,rm,fg)
        frappe.db.commit()
        c['transaction']='committed'
        c['outcome']='native cancel/amend executed; compare semantics, not project acceptance'
    except Exception:
        frappe.db.rollback()
        c['transaction']='rolled back'
        c['traceback']=traceback.format_exc()
        c['outcome']='error'
finally:
    frappe.db.rollback()
    frappe.db.set_single_value('Manufacturing Settings',dict(old_settings))
    frappe.db.commit()
    result['settings_restored']={key:frappe.db.get_single_value('Manufacturing Settings',key) for key in old_settings} == old_settings
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    with output.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,default=str)
    print(json.dumps({'output':str(output),'cases':[{k:c.get(k) for k in ['case','outcome','exception_class','transaction']} for c in result['cases']]},ensure_ascii=False))
