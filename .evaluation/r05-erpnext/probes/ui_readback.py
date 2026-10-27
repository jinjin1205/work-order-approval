import argparse,json,urllib.request,urllib.parse
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--stage',required=True);args=p.parse_args()
base=Path('.evaluation/r05-erpnext')
c=json.loads((base/'access-secrets.json').read_text())['users']['a']
fixture=json.loads(Path('evidence/R05/followup/access-setup.json').read_text())['fixtures']['UI']
result={'checked_utc':datetime.now(timezone.utc).isoformat(),'stage':args.stage,'user':c['email'],'observed':{}}
for doctype,key in [('Job Card','job_card'),('Work Order','work_order')]:
 url='http://127.0.0.1:18085/api/resource/'+urllib.parse.quote(doctype,safe='')+'/'+urllib.parse.quote(fixture[key],safe='')
 req=urllib.request.Request(url,headers={'Authorization':'token '+c['api_key']+':'+c['api_secret'],'Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as response: result['observed'][doctype]=json.load(response)['data']
output=Path('evidence/R05/followup/mobile')/(args.stage+'.json')
with output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
card=result['observed']['Job Card'];wo=result['observed']['Work Order']
print(json.dumps({'stage':args.stage,'docstatus':card['docstatus'],'card_completed':card['total_completed_qty'],'time_rows':len(card['time_logs']),'wo_operation_completed':[r['completed_qty'] for r in wo['operations']],'wo_produced':wo['produced_qty']},ensure_ascii=False))
