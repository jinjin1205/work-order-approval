import os,json
from pathlib import Path
import frappe
import frappe.share
from b08_distinct_concurrency_fixture import compare_tables,preserved
p=Path('/tmp/b08-private/b15-plan/access.json');os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads(p.read_text());user=a['actors']['other']['user'];frappe.get_doc('User',user).remove_roles(a['role']);frappe.share.add('Production Plan',a['plan'],user,read=1,write=0,notify=0)
 frappe.set_user(user);plan=frappe.get_doc('Production Plan',a['plan']);assert frappe.has_permission('Production Plan','read',doc=plan);assert not frappe.has_permission('Production Plan','write',doc=plan)
 frappe.set_user('Administrator');assert preserved(compare_tables(json.loads((p.parent/'before.json').read_text())));frappe.db.commit();print('Only new actor role revoked; native single-object read share retained, no write')
finally:frappe.db.rollback();frappe.destroy()
