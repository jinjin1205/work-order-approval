import os,json
from pathlib import Path
import frappe
from frappe.permissions import update_permission_property
os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads(Path('/tmp/b08-private/b16-query/access.json').read_text());role=a['roles']['read'];fields=['read','write','create','delete','submit','cancel','report','export','share','import']
 before=frappe.get_all('Custom DocPerm',filters={'role':role},fields=['parent']+fields);print(json.dumps({'before':before}))
 for row in before:
  for key in fields:
   expected=int(key=='read' or(key=='report'and row.parent in ['Work Order','Job Card','Stock Entry']))
   if row[key]!=expected:update_permission_property(row.parent,role,0,key,expected)
 frappe.db.commit();print('New read-only role set explicitly; no change to exporter or existing roles')
finally:frappe.db.rollback();frappe.destroy()
