import os,json,secrets
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission,update_permission_property
from frappe.utils.password import update_password
from b16_query_fixture import verify_retention
P=Path('/tmp/b08-private/b16-query');os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads((P/'access.json').read_text());assert 'history'not in a['actors'];new=frappe.get_doc('Job Card','[本地样例编号已移除]-1');old=frappe.get_doc('Job Card',new.amended_from);order=frappe.get_doc('Work Order',new.work_order);assert new.docstatus==1 and old.docstatus==2 and old.work_order==order.name and order.company==a['company']
 for role in a['roles'].values():
  for dt in ['Company','Department','Item','Warehouse','BOM','Operation','Workstation','Fiscal Year']:update_permission_property(dt,role,0,'export',0)
 user=frappe.get_doc({'doctype':'User','email':a['prefix']+'-history@example.invalid','first_name':'更正追溯查询','language':'zh','user_type':'System User','send_welcome_email':0,'roles':[{'role':a['roles']['export']}]}).insert();password=secrets.token_urlsafe(24);update_password(user.name,password);user.reload();user.api_key=frappe.generate_hash(length=15);user.api_secret=frappe.generate_hash(length=32);user.save();a['actors']['history']={'user':user.name,'password':password,'api_key':user.api_key,'api_secret':user.get_password('api_secret')};add_user_permission('Company',order.company,user.name);add_user_permission('Department',order.production_team,user.name,applicable_for='Work Order');add_user_permission('Work Order',order.name,user.name)
 a['history']={'order':order.name,'original':old.name,'corrected':new.name,'old_good':old.total_completed_qty,'new_good':new.total_completed_qty};checks,exceptions=verify_retention(json.loads((P/'before.json').read_text()));(P/'access.json').write_text(json.dumps(a));frappe.db.commit();print(json.dumps({'source':a['history'],'new_business_docs':0},ensure_ascii=False))
finally:frappe.db.rollback();frappe.destroy()
