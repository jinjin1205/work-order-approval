"""Persistent B14 synthetic config/user only; keep every pre-existing row unchanged."""
import hashlib,json,os,secrets,sys
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission
from frappe.utils.password import update_password
from b08_distinct_concurrency_fixture import capture_tables,compare_tables,preserved,write_private
from b10_issue_fixture import TABLES
P=Path('/tmp/b08-private/b14-config')
CONFIG_TABLES=['Document Naming Rule','Document Naming Rule Condition','DefaultValue','Property Setter','Production Time Rule','Production Time Period']

def prepare():
 assert not (P/'access.json').exists(),'Never recreate a completed fixture'
 if (P/'before.json').exists():
  before=json.loads((P/'before.json').read_text());assert preserved(compare_tables(before)), 'Failed preparation changed old rows'
 else:
  before=capture_tables(TABLES+CONFIG_TABLES);write_private(P/'before.json',before)
 old_info=json.loads(Path('/tmp/b08-private/b13-mobile/access.json').read_text());old=frappe.get_doc('Work Order',old_info['cases']['ui']['order']);prefix='b14-config-'+frappe.generate_hash(length=8)
 a={'site':frappe.local.site,'base_url':'http://127.0.0.1:18090','prefix':prefix,'company':old.company,'team':old.production_team,'actors':{},'orders':[]}
 source=frappe.get_doc('Item',old.production_item);item=frappe.copy_doc(source);item.item_code=prefix+'-fg';item.item_name=prefix+'-成品';item.default_bom=None
 for row in item.item_defaults:row.default_bom=None
 item.insert()
 bom=frappe.copy_doc(frappe.get_doc('BOM',old.bom_no));bom.item=item.name;bom.docstatus=0;bom.insert().submit()
 roles=[r.role for r in frappe.get_doc('User',old_info['actors']['editor']['user']).roles if r.role!='生产报工'];assert 'System Manager' not in roles
 for alias,actor_roles in [('manager',['System Manager']),('operator',roles)]:
  user=frappe.get_doc({'doctype':'User','email':prefix+'-'+alias+'@example.invalid','first_name':'配置管理员' if alias=='manager' else '配置消费发起人','language':'zh','time_zone':'Asia/Shanghai','user_type':'System User','send_welcome_email':0,'roles':[{'role':r}for r in actor_roles]}).insert();password=secrets.token_urlsafe(24);update_password(user.name,password);a['actors'][alias]={'user':user.name,'password':password}
 operator=a['actors']['operator']['user'];add_user_permission('Company',old.company,operator);add_user_permission('Department',old.production_team,operator,applicable_for='Work Order')
 a['default_permission']=frappe.db.get_value('User Permission',{'user':operator,'allow':'Company','for_value':old.company})
 a.update({'item':item.name,'bom':bom.name,'source_warehouse':old.source_warehouse,'wip_warehouse':old.wip_warehouse,'fg_warehouse':old.fg_warehouse,'rule_prefix':prefix.upper()+'-'})
 write_private(P/'access.json',a);checks=compare_tables(before);assert preserved(checks),checks;frappe.db.commit();return {'prepared':True,'old_tables_unchanged':len(checks),'new_users':2,'new_custom_fields':0,'business_entries':0}

def audit():
 before=json.loads((P/'before.json').read_text());a=json.loads((P/'access.json').read_text());checks=compare_tables(before);assert preserved(checks),checks
 orders=frappe.get_all('Work Order',filters={'production_item':a['item']},fields=['name','company','qty','docstatus','workflow_state','source_warehouse','bom_no'])
 for order in orders:assert order.docstatus==0 and order.workflow_state=='草稿';assert not frappe.db.exists('Job Card',{'work_order':order.name});assert not frappe.db.exists('Stock Entry',{'work_order':order.name})
 return {'old_rows_unchanged':True,'retention':checks,'orders':orders,'rules':frappe.get_all('Document Naming Rule',filters={'prefix':a['rule_prefix']},fields=['name','prefix','counter','disabled','priority']),'default_permission':frappe.get_doc('User Permission',a['default_permission']).as_dict(),'config_versions':frappe.get_all('Version',filters={'ref_doctype':'Document Naming Rule'},fields=['docname','creation'])}

if __name__=='__main__':
 os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True);os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
 try:
  assert frappe.conf.b08_http_only;frappe.set_user('Administrator');assert sys.argv[1] in ['prepare','audit'];print(json.dumps(prepare() if sys.argv[1]=='prepare' else audit(),ensure_ascii=False,default=str))
 finally:frappe.db.rollback();frappe.destroy()
