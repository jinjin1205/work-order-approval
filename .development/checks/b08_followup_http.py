"""Real HTTP for only new B08 followup boundaries; secrets/responses stay private."""
import json,subprocess,time,uuid
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
f=json.loads(Path('.development/private/b08-followup/http-fixture.json').read_text())
assert f['site']=='xgd-b08-http.localhost' and f['user'].startswith('b08-followup-')
api='http://127.0.0.1:18090/api/method/erpnext.manufacturing.doctype.job_card.job_card.'
headers={'Authorization':'token '+f['keys']['api_key']+':'+f['keys']['api_secret'],'Content-Type':'application/json','Host':f['site']}
results=[]
def request(label,method,args,expected):
    before=time.monotonic()
    req=Request(api+method,data=json.dumps(args).encode(),headers=headers,method='POST')
    try:
        with urlopen(req,timeout=30) as r:status=r.status;body=json.load(r)
    except HTTPError as error:
        status=error.code;body=json.load(error)
    results.append(dict(case=label,status=status,expected=expected,exception=body.get('exc_type'),seconds=round(time.monotonic()-before,3)))
    assert status==expected,(label,status,body.get('exc_type'))
    return body.get('message')
def control(mode):
    raw=subprocess.check_output(['docker','exec','xgd-b08-check','env/bin/python','/b01/b08_followup_http_fixture.py',mode],text=True)
    return json.loads(raw)
def denied(label,args,key,history_status):
    old=control('state')
    request(label+' preview','preview_production_report_time',{k:args[k] for k in ('work_order','operation_id','from_time','to_time')},403)
    request(label+' confirm stale page','confirm_production_report',args,403)
    found=request(label+' result','get_production_report_result',dict(request_id=key),history_status)
    assert control('state')==old,(label,'partial data change')
    results.append(dict(case=label+' zero partial write',passed=True,facts=old['facts'],good=old['good']))
    return found
try:
    assert control('state')['facts']==0,'Do not replay this consumed HTTP fixture'
    args=dict(work_order=f['order'],operation_id=f['operation_id'],from_time='2026-10-23 09:00',to_time='2026-10-23 10:00')
    preview=request('DEPT same department preview','preview_production_report_time',args,200)
    args.update(request_id=uuid.uuid4().hex,good_quantity=1,bad_quantity=0,context_fingerprint=preview['context_fingerprint'])
    first=request('DEPT same department confirm','confirm_production_report',args,200)
    new={**args,'request_id':uuid.uuid4().hex,'from_time':'2026-10-24 09:00','to_time':'2026-10-24 10:00'}
    preview=request('capture old page preview','preview_production_report_time',{k:new[k] for k in ('work_order','operation_id','from_time','to_time')},200)
    new['context_fingerprint']=preview['context_fingerprint']
    control('move_department')
    found=denied('DEPT employee moved',new,args['request_id'],200)
    assert found['name']==first['name']
    control('restore')
    for mode in ('revoke_company','revoke_team'):
        control(mode)
        denied(mode,new,args['request_id'],403)
        control('restore')
    found=request('restored authorization reads original','get_production_report_result',dict(request_id=args['request_id']),200)
    assert found['name']==first['name']
    assert control('state')['facts']==1
finally:
    control('restore')
    Path('evidence/B08/followup-20261028/http-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(http_checks=len([r for r in results if 'status' in r]),zero_partial_write_groups=3,retained_facts=1,passed=True)))
