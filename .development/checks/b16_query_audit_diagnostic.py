import os,json
from pathlib import Path
import frappe
from b08_distinct_concurrency_fixture import compare_tables,capture_tables
P=Path('/tmp/b08-private/b16-query');os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');before=json.loads((P/'before.json').read_text());checks=compare_tables(before);out={}
 for table,v in checks.items():
  if v['missing']or v['changed']:
   current=capture_tables([table])[table];out[table]={'counts':v,'baseline_shape':str(type(before[table])),'baseline_keys':list(before[table])[:3],'current_keys':list(current)[:3]}
 print(json.dumps(out,ensure_ascii=False))
finally:frappe.db.rollback();frappe.destroy()
