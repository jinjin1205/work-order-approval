"""Read-only real native run/export checks; results stay private, no retries."""
import csv,io,json,sys,urllib.request,urllib.error
from pathlib import Path
P=Path('.development/private/b16-query-20261031');A=json.loads((P/'access.json').read_text())
def request(method,args,alias='reader',expect=200):
 actor=A['actors'][alias];req=urllib.request.Request(A['base_url']+'/api/method/'+method,data=json.dumps(args).encode(),headers={'Host':A['site'],'Authorization':'token '+actor['api_key']+':'+actor['api_secret'],'Content-Type':'application/json','Accept-Language':'zh'})
 try:
  with urllib.request.urlopen(req,timeout=35)as r:status=r.status;body=r.read();mime=r.headers.get('Content-Type')
 except urllib.error.HTTPError as error:
  status=error.code;body=error.read();mime=error.headers.get('Content-Type')
 if status!=expect:
  (P/'http-unexpected.json').write_bytes(body);raise AssertionError((method,status,expect))
 return json.loads(body).get('message')if 'application/json'in(mime or '')else body

def run_checks():
 filters={'company':A['company'],'from_date':'2026-10-01','to_date':'2026-10-31','production_reports':1};summary={}
 for report,slug in [('Work Order Consumed Materials','materials'),('Job Card Summary','reports')]:
  result=json.loads((P/'materials-run.json').read_text()) if slug=='materials' and '--resume-materials' in sys.argv else request('frappe.desk.query_report.run',{'report_name':report,'filters':filters});(P/(slug+'-run.json')).write_text(json.dumps(result,ensure_ascii=False,default=str,indent=2));rows=result['result'];ids={r['name']for r in rows}
  args={'report_name':report,'filters':json.dumps(filters),'file_format_type':'CSV','visible_idx':'[]','export_in_background':0}
  content=(P/'materials.csv').read_bytes() if slug=='materials' and '--resume-materials' in sys.argv else request('frappe.desk.query_report.export_query',args);assert isinstance(content,bytes);(P/(slug+'.csv')).write_bytes(content);table=list(csv.reader(io.StringIO(content.decode('utf-8-sig'))));export_ids={row[0]for row in table[1:]if row};assert export_ids==ids,(ids,export_ids)
  assert A['restricted_order'] not in content.decode('utf-8-sig');assert all(r.get('work_order',r['name'])in A['orders']for r in rows)
  request('frappe.desk.query_report.export_query',args,alias='noexport',expect=403)
  summary[slug]={'rows':len(rows),'csv_rows':len(table)-1,'headers':table[0],'read_not_export':True}
 materials=json.loads((P/'materials-run.json').read_text())['result'];row=next(x for x in materials if x['name']=='[本地样例编号已移除]');assert(row['transferred_qty'],row['returned_qty'],row['net_qty'],row['consumed_qty'],row['consumption_status'])==(10,2,8,None,'未记录')
 query=dict(filters,work_order=[A['orders'][0],A['restricted_order']]);request('frappe.desk.query_report.run',{'report_name':'Job Card Summary','filters':query},expect=403)
 own=request('frappe.desk.query_report.run',{'report_name':'Work Order Consumed Materials','filters':dict(filters,name=A['restricted_order'])},alias='restricted');(P/'restricted-own-materials.json').write_text(json.dumps(own,ensure_ascii=False,indent=2));assert {r['name']for r in own['result']}=={A['restricted_order']}
 fields=['name','qty','produced_qty','stock_uom','workflow_state','status'];base={'doctype':'Work Order','fields':json.dumps(fields),'file_format_type':'CSV','page_length':0,'order_by':'name','translate_values':'1'}
 for label,extra in [('no-filter',{}),('mixed',{'selected_items':json.dumps([A['orders'][0],A['restricted_order']])}),('like',{'filters':json.dumps([['name','like','[本地样例编号已移除]%']])}),('quotes',{'filters':json.dumps([['name','like',"%'%"]])}),('not-equal',{'filters':json.dumps([['name','!=',A['orders'][0]]])})]:
  content=request('frappe.desk.reportview.export_query',dict(base,**extra));assert isinstance(content,bytes);(P/('list-'+label+'.csv')).write_bytes(content);rows=list(csv.reader(io.StringIO(content.decode('utf-8-sig'))));ids={r[1]for r in rows[1:]if r};assert ids<=set(A['orders']),ids
  if label=='no-filter':assert ids==set(A['orders'])
  if label=='mixed':assert ids=={A['orders'][0]}
  if label=='quotes':assert not ids
  if label=='not-equal':assert A['orders'][0]not in ids
  summary['list-'+label]={'rows':len(ids),'ids':sorted(ids)}
 request('frappe.desk.reportview.export_query',base,alias='noexport',expect=403)
 (P/'http-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({k:v.get('rows')for k,v in summary.items()},ensure_ascii=False))
if __name__=='__main__':run_checks()
