import json
import sys
from pathlib import Path
import b19_remaining_http as http

P=Path('.development/private/a01-boundary-20261031')
A=json.loads((P/'access.json').read_text())
http.P=P;http.A=A
call=http.call
WO=http.WO
AI='erpnext.manufacturing.production_ai.'
REPORT='erpnext.manufacturing.doctype.job_card.job_card.'


def prepare_order():
    doc=call('order-empty','frappe.client.insert',{'doc':dict(doctype='Work Order',production_item=A['fg'],bom_no=A['bom'],
        company=A['company'],production_team=A['team'],qty=10,stock_uom=A['unit'],expected_delivery_date='2026-11-07',
        source_warehouse=A['warehouses']['source'],wip_warehouse=A['warehouses']['wip'],fg_warehouse=A['warehouses']['fg'])},'planner')
    preview=call('order-details-preview',WO+'preview_production_order_details',dict(work_order=doc['name'],expected_modified=doc['modified']),'planner')
    call('order-details-confirm',WO+'confirm_production_order_details',dict(work_order=doc['name'],expected_modified=doc['modified'],fingerprint=preview['fingerprint']),'planner')
    doc=call('order-before-scope','frappe.client.get',dict(doctype='Work Order',name=doc['name']),'planner')
    doc['operations'][0]['report_scope']='ALL'
    doc=call('order-scope-save','frappe.client.save',{'doc':doc},'planner')
    for actor,action in [('planner','送审'),('reviewer','审核通过'),('director','签批通过')]:
        doc=call('order-prerequisite-'+actor,WO+'apply_production_approval',dict(work_order=doc['name'],action=action,expected_modified=doc['modified']),actor)
    case=dict(order=doc['name'],operation_id=doc['operations'][0]['name'])
    (P/'case.json').write_text(json.dumps(case,indent=2)+'\n')
    context=call('reader-context',AI+'get_production_ai_context',{'work_order':doc['name']},'reader')
    assert context['source']['name']==doc['name']and len(context['tasks'])==3
    draft=call('worker-draft',AI+'prepare_production_report_draft',dict(work_order=case['order'],operation_id=case['operation_id'],suggestion={'good_quantity':8,'bad_quantity':2}),'worker')
    assert set(draft['missing'])=={'from_time','to_time'}
    (P/'draft.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(order=doc['name'],structured_draft=True,missing_actual_times=True,model_invocations=0)))


def read_only_denials():
    case=json.loads((P/'case.json').read_text());draft=json.loads((P/'draft.json').read_text())
    args=dict(work_order=case['order'],operation_id=case['operation_id'],good_quantity=8,bad_quantity=2,
        from_time='2026-10-20 09:00:00',to_time='2026-10-20 10:00:00')
    preview=call('human-time-prerequisite',REPORT+'preview_production_report_time',args,'worker')
    call('reader-confirm-denied',REPORT+'confirm_production_report',dict(args,request_id='a01_reader_denied_request_001',
        context_fingerprint=preview['context_fingerprint'],draft_basis=draft['basis']),'reader',expected=403)
    call('reader-approval-denied',WO+'apply_production_approval',dict(work_order=case['order'],action='停止执行',
        expected_modified=draft['basis']['modified'],reason='只读身份不得执行'),'reader',expected=403)
    call('reader-stock-denied',WO+'make_stock_entry',dict(work_order_id=case['order'],purpose='Material Transfer for Manufacture',qty=1),'reader',expected=403)
    print(json.dumps(dict(read_positive=True,report_status=403,approval_status=403,stock_status=403)))


if __name__=='__main__':
    {'prepare-order':prepare_order,'read-only-denials':read_only_denials}[sys.argv[1]]()
