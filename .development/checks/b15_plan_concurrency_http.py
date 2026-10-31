"""Two real HTTP requests on one new plan row; no automatic retry."""
import concurrent.futures,json,threading,time,urllib.request,urllib.error
from pathlib import Path
p=Path('.development/private/b15-plan-20261031');a=json.loads((p/'access.json').read_text());actor=a['actors']['operator'];base=a['base_url'];method='erpnext.manufacturing.doctype.production_plan.production_plan.'
def call(name,args):
 req=urllib.request.Request(base+'/api/method/'+method+name,data=json.dumps(args).encode(),headers={'Host':a['site'],'Authorization':'token '+actor['api_key']+':'+actor['api_secret'],'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=40)as r:return json.load(r)['message']
 except urllib.error.HTTPError as error:
  body=json.loads(error.read());(p/('http-error-'+str(threading.get_ident())+'.json')).write_text(json.dumps(body));raise
args={'production_plan':a['concurrency_plan'],'production_plan_item':a['concurrency_row'],'production_team':a['team'],'expected_delivery_date':a['delivery']};preview=call('preview_approval_work_order',args);args['fingerprint']=preview['fingerprint'];barrier=threading.Barrier(2)
def worker(i):
 barrier.wait();start=time.monotonic();result=call('confirm_approval_work_order',args);return {'worker':i,'start':start,'end':time.monotonic(),'result':result}
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(worker,[1,2]))
assert len({x['result']['work_order']for x in results})==1,results
assert sorted(x['result']['already_exists']for x in results)==[False,True],results
assert max(x['start']for x in results)<min(x['end']for x in results),results
(p/'http-concurrency.json').write_text(json.dumps({'overlapping_requests':True,'results':results},indent=2));print(json.dumps({'requests':2,'same_order':results[0]['result']['work_order'],'created':1,'reused':1,'overlap':True}))
