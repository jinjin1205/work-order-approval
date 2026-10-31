import json,os
from pathlib import Path
import frappe
from b08_distinct_concurrency_fixture import compare_tables,preserved
p=Path('/tmp/b08-private/b15-plan/access.json');os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads(p.read_text());assert not a.get('concurrency_plan')
 plan=frappe.copy_doc(frappe.get_doc('Production Plan',a['plan']));plan.docstatus=0;plan.set('po_items',[dict(plan.po_items[0].as_dict(),name=None,parent=None)]);plan.insert().submit();a['concurrency_plan']=plan.name;a['concurrency_row']=plan.po_items[0].name
 assert preserved(compare_tables(json.loads((p.parent/'before.json').read_text())))
 p.write_text(json.dumps(a));frappe.db.commit();print('New independent plan prepared for fixed concurrency check')
finally:frappe.db.rollback();frappe.destroy()
