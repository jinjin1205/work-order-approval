"""Resume recorded stages of one real native HTTP chain; never replay successful writes."""
import csv
import io
import json
import sys
import uuid
from pathlib import Path

import b16_query_http as native

P = Path('.development/private/b17-core-20261031')
A = json.loads((P/'access.json').read_text())
native.P, native.A = P, A
WO = 'erpnext.manufacturing.doctype.work_order.work_order.'
JC = 'erpnext.manufacturing.doctype.job_card.job_card.'


def call(label, method, args, actor, expect=200):
    saved = P/(A.get('stage_prefix','')+label+'.json')
    if saved.exists():
        return json.loads(saved.read_text())
    try:
        result = native.request(method, args, alias=actor, expect=expect)
    except AssertionError:
        failure=P/'http-unexpected.json'
        if failure.exists():
            index=len(list(P.glob(label+'-failure-*.json')))+1
            (P/f'{label}-failure-{index}.json').write_bytes(failure.read_bytes())
        raise
    saved.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    with (P/'requests.jsonl').open('a') as log:
        log.write(json.dumps(dict(label=label, method=method, actor=actor, expected_status=expect,
                                  status=expect), ensure_ascii=False)+'\n')
    return result


def order(label, actor='planner'):
    return call(label, 'frappe.client.get', {'doctype':'Work Order','name':A['order']}, actor)


def post_stock(label, draft):
    doc = call(label+'-insert', 'frappe.client.insert', {'doc':draft}, 'warehouse')
    return call(label+'-submit', 'frappe.client.submit', {'doc':doc}, 'warehouse')


def create():
    doc = dict(doctype='Work Order', production_item=A['fg'], bom_no=A['bom'], company=A['company'],
        production_team=A['team'], qty=10, stock_uom=A['unit'], expected_delivery_date='2026-11-07',
        planned_start_date='2026-10-31 08:00:00', source_warehouse=A['warehouses']['source'],
        wip_warehouse=A['warehouses']['wip'], fg_warehouse=A['warehouses']['fg'])
    if 'previous_order' in A:
        doc['previous_work_order']=A['previous_order']
    created = call('01-empty', 'frappe.client.insert', {'doc':doc}, 'planner')
    assert not created['operations'] and not created['required_items']
    print(json.dumps({'empty_order':created['name'],'operations':0,'materials':0}))


def approve():
    doc = order('02-before-details')
    args = dict(work_order=A['order'], expected_modified=doc['modified'])
    preview = call('03-details-preview', WO+'preview_production_order_details', args, 'planner')
    call('04-details-confirm', WO+'confirm_production_order_details', dict(args,fingerprint=preview['fingerprint']), 'planner')
    doc = order('05-details')
    assert len(doc['operations'])==3 and len(doc['required_items'])==1 and doc['required_items'][0]['required_qty']==5
    for row in doc['operations']:
        row.update(report_scope='DEPT',report_department=A['team'])
    doc=call('05-task-scope','frappe.client.save',{'doc':doc},'planner')
    for label,actor,action in [('06-request','planner','送审'),('07-review','reviewer','审核通过'),('08-sign','director','签批通过')]:
        doc=call(label, WO+'apply_production_approval', dict(work_order=A['order'],action=action,expected_modified=doc['modified']),actor)
    assert doc['docstatus']==1 and doc['workflow_state']=='已批准'
    assert doc['modified_by']==A['actors']['director']['user']
    assert len({doc['approval_requested_by'],doc['approval_reviewed_by'],doc['modified_by']})==3
    print(json.dumps({'approved':A['order'],'operations':3,'required':5}))


def material_cycle():
    draft=call('09-issue-draft',WO+'make_stock_entry',dict(work_order_id=A['order'],purpose='Material Transfer for Manufacture',qty=10),'warehouse')
    issue=post_stock('10-issue',draft)
    assert issue['items'][0]['transfer_qty']==5
    draft=call('11-return-draft',WO+'make_stock_return_entry',dict(work_order=A['order']),'warehouse')
    assert len(draft['items'])==1
    draft['items'][0]['qty']=1
    returned=post_stock('12-return',draft)
    summary=call('13-net-four',WO+'get_production_material_summary',dict(work_order=A['order']),'warehouse')
    assert summary['items'][0]['net']==4 and summary['items'][0]['returned']==1
    call('14-return-cancel','frappe.client.cancel',dict(doctype='Stock Entry',name=returned['name']),'warehouse')
    summary=call('15-net-five',WO+'get_production_material_summary',dict(work_order=A['order']),'warehouse')
    assert summary['items'][0]['net']==5 and summary['items'][0]['returned']==0
    print(json.dumps({'issue':issue['name'],'return':returned['name'],'effective_net_after_return_cancel':5}))


def report():
    doc=order('16-before-reports','worker')
    for i,op in enumerate(doc['operations']):
        args=dict(work_order=A['order'],operation_id=op['name'],from_time=f'2026-10-31 {8+i:02}:00:00',to_time=f'2026-10-31 {9+i:02}:00:00')
        preview=call(f'17-preview-{i}',JC+'preview_production_report_time',args,'worker')
        key_path=P/f'request-key-{i}.txt'
        if not key_path.exists():key_path.write_text(uuid.uuid4().hex)
        call(f'18-report-{i}',JC+'confirm_production_report',dict(args,request_id=key_path.read_text(),good_quantity=10,bad_quantity=0,context_fingerprint=preview['context_fingerprint']),'worker')
        current=order(f'19-progress-{i}','worker')
        assert sum(op['completed_qty']==10 for op in current['operations'])==i+1
        assert current['produced_qty']==0
    print(json.dumps({'reports':3,'per_operation_good':10,'finished_receipts':0}))


def manufacture():
    first=call('20-manufacture-four-draft',WO+'make_stock_entry',dict(work_order_id=A['order'],purpose='Manufacture',qty=4),'warehouse')
    post_stock('21-manufacture-four',first)
    doc=order('22-partial','warehouse');assert doc['produced_qty']==4
    remaining=call('23-remaining',WO+'make_stock_entry',dict(work_order_id=A['order'],purpose='Manufacture',quantity_only=1),'warehouse')
    assert remaining['fg_completed_qty']==6
    second=call('24-manufacture-six-draft',WO+'make_stock_entry',dict(work_order_id=A['order'],purpose='Manufacture',qty=6),'warehouse')
    post_stock('25-manufacture-six',second)
    doc=order('26-completed','warehouse')
    assert doc['produced_qty']==10 and doc['required_items'][0]['consumed_qty']==5
    print(json.dumps({'first':4,'second':6,'finished':10,'consumed':5}))


def reconcile(*, reversed_chain=False):
    filters=dict(company=A['company'],from_date='2026-10-01',to_date='2026-10-31')
    phase='after-reverse-' if reversed_chain else ''
    for label,report_name,extra in [('materials','Work Order Consumed Materials',{'name':A['order']}),('reports','Job Card Summary',{'work_order':[A['order']],'production_reports':1})]:
        f=dict(filters,**extra)
        result=call(phase+'27-'+label,'frappe.desk.query_report.run',dict(report_name=report_name,filters=f),'query')
        dest=P/(phase+'28-'+label+'.csv')
        if not dest.exists():
            content=native.request('frappe.desk.query_report.export_query',dict(report_name=report_name,filters=json.dumps(f),file_format_type='CSV',visible_idx='[]',export_in_background=0),alias='query')
            dest.write_bytes(content)
        rows=list(csv.reader(io.StringIO(dest.read_text(encoding='utf-8-sig'))))
        assert {r[0] for r in rows[1:]}=={r['name'] for r in result['result']}
        if label=='materials':
            row=result['result'][0]
            expected=(5,0,0,0,None,0) if reversed_chain else (5,5,0,5,5,10)
            assert (row['required_qty'],row['transferred_qty'],row['returned_qty'],row['net_qty'],row['consumed_qty'],row['produced_qty'])==expected
        else:
            assert sorted(r['good_qty'] for r in result['result'])==([8,10,10] if reversed_chain else [10,10,10])
            if reversed_chain:
                changed=next(r for r in result['result'] if r['good_qty']==8)
                assert changed['amended_from']==json.loads((P/(A.get('stage_prefix','')+'18-report-2.json')).read_text())['name']
    print(json.dumps({'material_rows':1,'report_rows':3,'csv_matches':True}))


def recover_scope():
    issue=json.loads((P/'10-issue-submit.json').read_text())
    call('recovery-cancel-issue','frappe.client.cancel',dict(doctype='Stock Entry',name=issue['name']),'warehouse')
    doc=order('recovery-before-cancel','director')
    stopped=call('recovery-stop-order',WO+'apply_production_approval',dict(work_order=A['order'],action='停止执行',expected_modified=doc['modified'],reason='B17合成样例漏配任务报工范围，保留历史后关联新单'),'director')
    assert stopped['status']=='Stopped'
    A['previous_order']=A['order'];A['stage_prefix']='continuation-'
    create()


def reverse():
    prefix=A.get('stage_prefix','')
    report=json.loads((P/(prefix+'18-report-2.json')).read_text())
    key_path=P/'correction-key.txt'
    if not key_path.exists():key_path.write_text(uuid.uuid4().hex)
    args=dict(original_job_card=report['name'],request_id=key_path.read_text(),good_quantity=8,bad_quantity=0,
              reason='B17逆序处理后更正最后工序，原记录保留')
    call('29-correction-stock-refused',JC+'correct_production_report',args,'worker',expect=417)
    for label,source in [('30-cancel-six','25-manufacture-six-submit'),('31-cancel-four','21-manufacture-four-submit'),('32-cancel-issue','10-issue-submit')]:
        doc=json.loads((P/(prefix+source+'.json')).read_text())
        call(label,'frappe.client.cancel',dict(doctype='Stock Entry',name=doc['name']),'warehouse')
    before=order('33-before-correction','worker')
    assert before['produced_qty']==0 and before['required_items'][0]['consumed_qty']==0
    corrected=call('34-corrected',JC+'correct_production_report',args,'worker')
    original=call('35-original-preserved','frappe.client.get',dict(doctype='Job Card',name=report['name']),'worker')
    replacement=call('36-correction-source','frappe.client.get',dict(doctype='Job Card',name=corrected['name']),'worker')
    assert original['docstatus']==2 and original['total_completed_qty']==10
    assert replacement['docstatus']==1 and replacement['total_completed_qty']==8 and replacement['amended_from']==original['name']
    final=order('37-after-correction','worker')
    assert [op['completed_qty'] for op in final['operations']]==[10,10,8]
    print(json.dumps({'original':original['name'],'corrected':replacement['name'],'old_good':10,'effective_good':8,'finished':final['produced_qty']}))


if __name__=='__main__':
    stages={'create':create,'approve':approve,'materials':material_cycle,'report':report,'manufacture':manufacture,'reconcile':reconcile,'recover-scope':recover_scope,'reverse':reverse,'reverse-reconcile':lambda:reconcile(reversed_chain=True)}
    stages[sys.argv[1]]()
