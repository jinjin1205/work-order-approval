import csv,io,json
from b16_query_http import A,P,request
fields=['name','docstatus','purpose','is_return','work_order','`tabStock Entry Detail`.`against_stock_entry`','`tabStock Entry Detail`.`item_code`','`tabStock Entry Detail`.`transfer_qty`','`tabStock Entry Detail`.`stock_uom`']
args={'doctype':'Stock Entry','fields':json.dumps(fields),'filters':json.dumps([['work_order','=','[本地样例编号已移除]']]),'file_format_type':'CSV','page_length':0,'order_by':'name','translate_values':'1'}
content=request('frappe.desk.reportview.export_query',args);(P/'stock-source.csv').write_bytes(content);rows=list(csv.reader(io.StringIO(content.decode('utf-8-sig'))));ids={r[1]for r in rows[1:]if r};assert ids=={'[本地样例编号已移除]','[本地样例编号已移除]'},ids;assert '[本地样例编号已移除]'in next(r for r in rows[1:]if r[1]=='[本地样例编号已移除]');print(json.dumps({'ids':sorted(ids),'rows':len(rows)-1,'headers':rows[0]},ensure_ascii=False))
