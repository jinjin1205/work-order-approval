"""Real HTTP requests against only the retained synthetic B08 site."""
import concurrent.futures, json, threading, time, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError
f=json.loads(Path('.development/private/b08-http/fixture.json').read_text())
assert f['site']=='xgd-b08-http.localhost' and f['base_url']=='http://127.0.0.1:18090'
api='erpnext.manufacturing.doctype.job_card.job_card.'
headers={'Authorization':'token '+f['keys']['api_key']+':'+f['keys']['api_secret'], 'Content-Type':'application/json','Host':f['site']}
results=[]
def call(method,args,verb='POST',resource=False):
    path='/api/resource/'+quote(method,safe='/') if resource else '/api/method/'+api+method
    body=json.dumps(args).encode() if args is not None else None
    req=Request(f['base_url']+path,data=body,headers=headers,method=verb)
    start=time.monotonic()
    try:
        with urlopen(req,timeout=35) as response: status=response.status; data=json.load(response)
    except HTTPError as error:
        status=error.code;data=json.load(error)
    return dict(status=status,data=data,start=start,end=time.monotonic())
def check(label,result,status):
    results.append(dict(case=label,status=result['status'],expected=status,exception=result['data'].get('exc_type'),elapsed_seconds=round(result['end']-result['start'],3)))
    assert result['status']==status,(label,result['status'],result['data'].get('exception'))
    return result['data'].get('message',result['data'].get('data'))
def args_for(good,start,end):
    args=dict(work_order=f['http_order'],operation_id=f['http_operation_id'],from_time=start,to_time=end,shutdown_seconds=0,overtime_seconds=0)
    preview=check('preview',call('preview_production_report_time',args),200)
    return dict(**args,good_quantity=good,bad_quantity=0,request_id=uuid.uuid4().hex,context_fingerprint=preview['context_fingerprint'])
def facts():
    return check('task-readback',call('get_production_report_tasks',dict(work_order=f['http_order'])),200)
def run():
    try:
        baseline=facts();assert not baseline['reports'], 'Do not repeat HTTP batch on a consumed fixture'
        args=args_for(1,'2026-10-14 09:00','2026-10-14 10:00')
        barrier=threading.Barrier(2)
        def send():
            barrier.wait(); return call('confirm_production_report',args)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(send) for _ in range(2)]; replies=[v.result() for v in futures]
        Path('.development/private/b08-http/last-replies.json').write_text(json.dumps(replies,ensure_ascii=False,indent=2))
        names=[check('concurrent-same-key',r,200)['name'] for r in replies]
        assert names[0]==names[1]
        assert max(r['start'] for r in replies) < min(r['end'] for r in replies)
        after=facts();assert len(after['reports'])==1 and after['tasks'][0]['good']==1
        check('same-key-retry',call('confirm_production_report',args),200)
        check('same-key-different-content',call('confirm_production_report',{**args,'good_quantity':2}),403)
        # Distinct real report keys with identical quantities AND identical zero-duration inputs.
        equal=args_for(1,'2026-10-15 09:00','2026-10-15 09:00')
        a=check('identical-content-key-A',call('confirm_production_report',equal),200)
        b=check('identical-content-key-B',call('confirm_production_report',{**equal,'request_id':uuid.uuid4().hex}),200)
        assert a['name']!=b['name']
        before=facts();assert len(before['reports'])==3 and before['tasks'][0]['good']==3
        over=args_for(8,'2026-10-15 10:00','2026-10-15 11:00')
        check('real-overquantity-rollback',call('confirm_production_report',over),417)
        after=facts();assert before==after
        check('task-out-of-scope',call('preview_production_report_time',{**args,'operation_id':f['http_forbidden']}),403)
        check('parent-write-denied',call('Work Order/'+f['http_order'],{'qty':20},'PUT',True),403)
        card=check('original-read',call('Job Card/'+names[0],None,'GET',True),200)
        check('original-update-denied',call('Job Card/'+names[0],{'remarks':'tamper','flags':{'ignore_validate_update_after_submit':True}},'PUT',True),403)
        row=card['time_logs'][0]
        check('child-update-denied',call('Job Card Time Log/'+row['name'],{'completed_qty':9,'flags':{'ignore_validate_update_after_submit':True}},'PUT',True),403)
        found=check('lost-response-lookup',call('get_production_report_result',{'request_id':args['request_id']}),200)
        assert found['name']==names[0]
        final=facts();assert final==before
        results.append(dict(case='final',facts=3,good=3,bad=0,plan=10,same_key_parallel_http=True,full_concurrency_gate_closed=False))
    finally:
        Path('evidence/B08/implementation/http-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')

if __name__ == "__main__":
    run()
