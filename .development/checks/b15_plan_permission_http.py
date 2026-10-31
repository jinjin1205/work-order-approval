import json,urllib.request,urllib.error
from pathlib import Path
p=Path('.development/private/b15-plan-20261031');a=json.loads((p/'access.json').read_text());actor=a['actors']['other'];args={'production_plan':a['plan'],'production_plan_item':a['rows'][0],'production_team':a['team'],'expected_delivery_date':a['delivery']}
results=[]
for method in ['preview_approval_work_order','confirm_approval_work_order']:
 payload=dict(args)
 if method.startswith('confirm'):payload['fingerprint']='revoked-not-authorized'
 req=urllib.request.Request(a['base_url']+'/api/method/erpnext.manufacturing.doctype.production_plan.production_plan.'+method,data=json.dumps(payload).encode(),headers={'Host':a['site'],'Authorization':'token '+actor['api_key']+':'+actor['api_secret'],'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=15)as r:raise AssertionError('Unexpected authorized response '+str(r.status))
 except urllib.error.HTTPError as error:
  body=json.loads(error.read());assert error.code==403,(error.code,body);assert body.get('exc_type')=='PermissionError',body;results.append({'method':method,'status':error.code,'exception':body['exc_type']})
(p/'http-permissions.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
