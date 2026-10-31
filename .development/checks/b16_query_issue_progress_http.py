import json,sys
from b16_query_http import A,P,request
filters={'company':A['company'],'from_date':'2026-10-01','to_date':'2026-10-31','name':'[本地样例编号已移除]'}
r=request('frappe.desk.query_report.run',{'report_name':'Work Order Consumed Materials','filters':filters});row=r['result'][0];assert row['material_issue_percent']==100,row;assert row['net_qty']==8;print(json.dumps({'issued':row['transferred_qty'],'returned':row['returned_qty'],'net':row['net_qty'],'issue_percent':row['material_issue_percent']}))
