import csv,io,json
from b16_query_http import A,P,request
h=A['history'];evidence={}
for state,expected in [('生效',h['corrected']),('已取消',h['original'])]:
 filters={'company':A['company'],'from_date':'2026-10-01','to_date':'2026-10-31','production_reports':1,'report_state':state,'work_order':[h['order']]};result=request('frappe.desk.query_report.run',{'report_name':'Job Card Summary','filters':filters},alias='history');row=next(r for r in result['result']if r['name']==expected)
 if state=='生效':assert row['amended_from']==h['original'] and row['good_qty']==h['new_good']
 else:assert row['good_qty']==h['old_good']
 content=request('frappe.desk.query_report.export_query',{'report_name':'Job Card Summary','filters':json.dumps(filters),'file_format_type':'CSV','visible_idx':'[]','export_in_background':0},alias='history');rows=list(csv.reader(io.StringIO(content.decode('utf-8-sig'))));assert {r[0]for r in rows[1:]if r}=={r['name']for r in result['result']};slug='effective'if state=='生效'else'cancelled';(P/('history-'+slug+'.csv')).write_bytes(content);evidence[state]=result
(P/'history-query.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2));print(json.dumps({state:[{'name':r['name'],'good':r['good_qty'],'original':r['amended_from']}for r in data['result']]for state,data in evidence.items()},ensure_ascii=False))
