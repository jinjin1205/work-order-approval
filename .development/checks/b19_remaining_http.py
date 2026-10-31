"""Ordinary actors prepare only new B19 scenarios; preserve raw native responses."""
import json
import sys
import urllib.error
import urllib.request
import urllib.parse
import hashlib
from pathlib import Path

P=Path('.development/private/b19-remaining-20261031')
A=json.loads((P/'access.json').read_text())
WO='erpnext.manufacturing.doctype.work_order.work_order.'


def call(label,method,args,actor,expected=200):
    target=P/(label+'.json')
    assert not target.exists(),'Inspect the retained result before repeating a request: '+label
    user=A['actors'][actor]
    request=urllib.request.Request(A['base_url']+'/api/method/'+method,data=json.dumps(args).encode(),headers={
        'Host':A['site'],'Authorization':'token '+user['api_key']+':'+user['api_secret'],
        'Content-Type':'application/json','Accept-Language':'zh'})
    try:
        with urllib.request.urlopen(request,timeout=35)as response:status=response.status;body=response.read()
    except urllib.error.HTTPError as error:
        status=error.code;body=error.read()
    result=json.loads(body)
    target.write_text(json.dumps({'method':method,'actor':actor,'status':status,'body':result},ensure_ascii=False,indent=2)+'\n')
    if expected is not None:
        assert status==expected,(label,status,expected)
    return result.get('message')


def sign_main():
    doc=call('main-before-review','frappe.client.get',{'doctype':'Work Order','name':'[本地样例编号已移除]'},'reviewer')
    assert doc['workflow_state']=='待审核' and doc['expected_delivery_date']=='2026-11-09'
    for label,actor,action in [('main-reviewed','reviewer','审核通过'),('main-signed','director','签批通过')]:
        doc=call(label,WO+'apply_production_approval',dict(work_order=doc['name'],action=action,expected_modified=doc['modified']),actor)
    assert doc['docstatus']==1 and doc['workflow_state']=='已批准'
    print(json.dumps({'main':doc['name'],'state':doc['workflow_state']}))


def prepare_stop():
    doc=call('stop-empty','frappe.client.insert',{'doc':dict(doctype='Work Order',production_item=A['fg'],bom_no=A['bom'],
        company=A['company'],production_team=A['team'],qty=10,stock_uom=A['unit'],expected_delivery_date='2026-11-07',
        source_warehouse=A['warehouses']['source'],wip_warehouse=A['warehouses']['wip'],fg_warehouse=A['warehouses']['fg'])},'planner')
    args=dict(work_order=doc['name'],expected_modified=doc['modified'])
    preview=call('stop-details-preview',WO+'preview_production_order_details',args,'planner')
    confirmed=call('stop-details-confirm',WO+'confirm_production_order_details',dict(args,fingerprint=preview['fingerprint']),'planner')
    version=confirmed['modified']
    for label,actor,action in [('stop-requested','planner','送审'),('stop-reviewed','reviewer','审核通过'),('stop-signed','director','签批通过')]:
        doc=call(label,WO+'apply_production_approval',dict(work_order=doc['name'],action=action,expected_modified=version),actor)
        version=doc['modified']
    draft=call('stop-issue-draft',WO+'make_stock_entry',dict(work_order_id=doc['name'],purpose='Material Transfer for Manufacture',qty=10),'warehouse')
    draft=call('stop-issue-insert','frappe.client.insert',{'doc':draft},'warehouse')
    issue=call('stop-issue-submit','frappe.client.submit',{'doc':draft},'warehouse')
    assert issue['docstatus']==1 and issue['items'][0]['transfer_qty']==5
    (P/'stop-case.json').write_text(json.dumps({'order':doc['name'],'issue':issue['name']},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'stop_order':doc['name'],'effective_issue':5}))


def prepare_draft(label):
    doc=call(label+'-empty','frappe.client.insert',{'doc':dict(doctype='Work Order',production_item=A['fg'],bom_no=A['bom'],
        company=A['company'],production_team=A['team'],qty=10,stock_uom=A['unit'],expected_delivery_date='2026-11-07',
        source_warehouse=A['warehouses']['source'],wip_warehouse=A['warehouses']['wip'],fg_warehouse=A['warehouses']['fg'])},'planner')
    args=dict(work_order=doc['name'],expected_modified=doc['modified'])
    preview=call(label+'-preview',WO+'preview_production_order_details',args,'planner')
    call(label+'-details',WO+'confirm_production_order_details',dict(args,fingerprint=preview['fingerprint']),'planner')
    return call(label+'-ready','frappe.client.get',dict(doctype='Work Order',name=doc['name']),'planner')


def attachment_start():
    doc=prepare_draft('attachment')
    file=call('attachment-v1','frappe.client.insert',{'doc':dict(doctype='File',file_name=A['prefix']+'-作业要求-v1.txt',
        content='B19真实HTTP合成作业要求v1',is_private=1,attached_to_doctype='Work Order',attached_to_name=doc['name'])},'planner')
    doc=call('attachment-before-send','frappe.client.get',dict(doctype='Work Order',name=doc['name']),'planner')
    doc=call('attachment-first-send',WO+'apply_production_approval',dict(work_order=doc['name'],action='送审',expected_modified=doc['modified']),'planner')
    transitions=call('revocation-before-transitions','frappe.model.workflow.get_transitions',{'doc':json.dumps(doc)},'revoked_reviewer')
    assert any(t['action']=='审核通过'for t in transitions)
    (P/'attachment-case.json').write_text(json.dumps({'order':doc['name'],'v1':file['name'],'v1_url':file['file_url'],'v1_hash':file['content_hash']},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'attachment_order':doc['name'],'first_sent':True,'revocation_positive_transition':True}))


def attachment_finish():
    case=json.loads((P/'attachment-case.json').read_text())
    doc=call('revocation-after-read','frappe.client.get',dict(doctype='Work Order',name=case['order']),'revoked_reviewer')
    call('revocation-after-action',WO+'apply_production_approval',dict(work_order=doc['name'],action='审核通过',expected_modified=doc['modified']),'revoked_reviewer',expected=403)
    doc=call('attachment-return',WO+'apply_production_approval',dict(work_order=doc['name'],action='退回',expected_modified=doc['modified'],reason='补充新版作业要求和交期'),'reviewer')
    v2=call('attachment-v2','frappe.client.insert',{'doc':dict(doctype='File',file_name=A['prefix']+'-作业要求-v2.txt',
        content='B19真实HTTP合成作业要求v2',is_private=1,attached_to_doctype='Work Order',attached_to_name=case['order'])},'planner')
    doc=call('attachment-before-edit','frappe.client.get',dict(doctype='Work Order',name=case['order']),'planner')
    doc['expected_delivery_date']='2026-11-10'
    doc=call('attachment-date-saved','frappe.client.save',{'doc':doc},'planner')
    doc=call('attachment-second-send',WO+'apply_production_approval',dict(work_order=doc['name'],action='送审',expected_modified=doc['modified']),'planner')
    original=call('attachment-v1-read','frappe.client.get',dict(doctype='File',name=case['v1']),'reviewer')
    assert original['content_hash']==case['v1_hash']
    changed=dict(original,file_name='不可改写.txt')
    call('attachment-http-rename-refused','frappe.client.save',{'doc':changed},'reviewer',expected=403)
    call('attachment-http-delete-refused','frappe.client.delete',dict(doctype='File',name=original['name']),'reviewer',expected=403)
    changed=dict(original,attached_to_name=json.loads((P/'stop-case.json').read_text())['order'])
    call('attachment-http-relink-refused','frappe.client.save',{'doc':changed},'reviewer',expected=403)
    call('attachment-http-late-insert-refused','frappe.client.insert',{'doc':dict(doctype='File',file_name=A['prefix']+'-晚加.txt',
        content='不能在送审后追加',is_private=1,attached_to_doctype='Work Order',attached_to_name=case['order'])},'reviewer',expected=403)
    doc=call('attachment-reviewed',WO+'apply_production_approval',dict(work_order=doc['name'],action='审核通过',expected_modified=doc['modified']),'reviewer')
    call('foreign-director-sign-refused',WO+'apply_production_approval',dict(work_order=doc['name'],action='签批通过',expected_modified=doc['modified']),'foreign_director',expected=403)
    doc=call('attachment-signed',WO+'apply_production_approval',dict(work_order=doc['name'],action='签批通过',expected_modified=doc['modified']),'director')
    case.update(v2=v2['name'],v2_url=v2['file_url'],v2_hash=v2['content_hash'])
    (P/'attachment-case.json').write_text(json.dumps(case,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'attachment_rounds':2,'v1_retained':True,'state':doc['workflow_state'],'permission_negative_status':403}))


def prepare_races():
    cases={}
    for case in ['double','withdraw','execute','fault']:
        label='race-'+case
        doc=prepare_draft(label)
        for step,actor,action in [('send','planner','送审'),('review','reviewer','审核通过')]:
            doc=call(label+'-'+step,WO+'apply_production_approval',dict(work_order=doc['name'],action=action,expected_modified=doc['modified']),actor)
        cases[case]={'order':doc['name'],'version':doc['modified']}
    (P/'race-cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'new_approval_race_cases':len(cases),'state':'待签批'}))


def pending_permission_probe():
    cases=json.loads((P/'race-cases.json').read_text())
    target=cases['double']['order']
    args=dict(doctype='Workflow Action',fields=['name','reference_doctype','reference_name','workflow_state'],
              filters={'reference_doctype':'Work Order','reference_name':target},limit_page_length=0)
    positive=call('pending-director-positive','frappe.client.get_list',args,'director')
    assert positive,'Need a real open action positive'
    negative=call('pending-foreign-director','frappe.client.get_list',args,'foreign_director')
    assert not negative,'Foreign-company actor can enumerate production approval action'


def pending_permission_green():
    target=json.loads((P/'race-cases.json').read_text())['execute']['order']
    base=dict(doctype='Workflow Action',fields=['name','reference_doctype','reference_name','workflow_state'],limit_page_length=0)
    exact=dict(base,filters={'reference_doctype':'Work Order','reference_name':target})
    own=call('pending-green-own','frappe.client.get_list',exact,'director')
    assert own
    assert not call('pending-green-foreign','frappe.client.get_list',exact,'foreign_director')
    leaked=json.loads((P/'pending-foreign-director.json').read_text())['body']['message'][0]
    call('pending-green-own-record','frappe.client.get',dict(doctype='Workflow Action',name=leaked['name']),'director')
    call('pending-green-foreign-record','frappe.client.get',dict(doctype='Workflow Action',name=leaked['name']),'foreign_director',expected=403)
    for label,op,value in [('like','like',target+'%'),('quotes','like',"%'%"),('not-equal','!=',target)]:
        rows=call('pending-green-filter-'+label,'frappe.client.get_list',dict(base,filters=[['reference_doctype','=','Work Order'],['reference_name',op,value]]),'director')
        if label=='like':assert {r['reference_name']for r in rows}=={target}
        if label=='quotes':assert not rows
        if label=='not-equal':assert all(r['reference_name']!=target for r in rows)
    print(json.dumps({'same_company_positive':True,'foreign_query_empty':True,'foreign_record_status':403,'filters':['like/%','quote','!=']}))


def download(label,url,actor):
    assert url.startswith('/private/files/')
    user=A['actors'][actor]
    request=urllib.request.Request(A['base_url']+urllib.parse.quote(url,safe='/%'),headers={
        'Host':A['site'],'Authorization':'token '+user['api_key']+':'+user['api_secret']})
    try:
        with urllib.request.urlopen(request,timeout=35)as response:status=response.status;body=response.read()
    except urllib.error.HTTPError as error:
        status=error.code;body=error.read()
    target=P/(label+'.json');assert not target.exists()
    result={'actor':actor,'status':status,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'native_content_hash':hashlib.md5(body).hexdigest()}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (P/(label+'.bin')).write_bytes(body)
    return result


def owner_before():
    case=json.loads((P/'attachment-case.json').read_text())
    call('owner-before-parent','frappe.client.get',dict(doctype='Work Order',name=case['order']),'planner')
    result=download('owner-before-download',case['v1_url'],'planner')
    assert result['status']==200 and result['native_content_hash']==case['v1_hash']
    print(json.dumps({'owner_download_positive':True}))


def owner_after_probe():
    case=json.loads((P/'attachment-case.json').read_text())
    call('owner-after-parent','frappe.client.get',dict(doctype='Work Order',name=case['order']),'planner',expected=403)
    call('owner-after-file','frappe.client.get',dict(doctype='File',name=case['v1']),'planner',expected=None)
    call('owner-after-file-list','frappe.client.get_list',dict(doctype='File',fields=['name','file_url'],
         filters={'attached_to_doctype':'Work Order','attached_to_name':case['order']},limit_page_length=0),'planner',expected=None)
    result=download('owner-after-download',case['v1_url'],'planner')
    metadata=json.loads((P/'owner-after-file.json').read_text());listed=json.loads((P/'owner-after-file-list.json').read_text())
    assert metadata['status']==403 and not listed['body'].get('message') and result['status']==403,{
        'metadata_status':metadata['status'],'list_rows':len(listed['body'].get('message')or []),'download_status':result['status']}


def owner_scope_green():
    case=json.loads((P/'attachment-case.json').read_text())
    call('owner-green-parent','frappe.client.get',dict(doctype='Work Order',name=case['order']),'planner',expected=403)
    call('owner-green-file','frappe.client.get',dict(doctype='File',name=case['v1']),'planner',expected=403)
    rows=call('owner-green-list','frappe.client.get_list',dict(doctype='File',fields=['name','file_url'],
         filters={'attached_to_doctype':'Work Order','attached_to_name':case['order']},limit_page_length=0),'planner')
    assert not rows
    denied=download('owner-green-download',case['v1_url'],'planner')
    assert denied['status']==403
    call('reader-green-file','frappe.client.get',dict(doctype='File',name=case['v1']),'reviewer')
    allowed=download('reader-green-download',case['v1_url'],'reviewer')
    assert allowed['status']==200 and allowed['native_content_hash']==case['v1_hash']
    print(json.dumps({'owner_metadata_status':403,'owner_download_status':403,'owner_list_rows':0,'authorized_reader_status':200,'original_bytes_match':True}))


if __name__=='__main__':
    {'sign-main':sign_main,'prepare-stop':prepare_stop,'attachment-start':attachment_start,'attachment-finish':attachment_finish,
     'prepare-races':prepare_races,'pending-permission':pending_permission_probe,'pending-green':pending_permission_green,
     'owner-before':owner_before,'owner-after':owner_after_probe,'owner-green':owner_scope_green}[sys.argv[1]]()
