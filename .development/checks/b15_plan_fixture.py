"""B15 new synthetic project, submitted plan, users; preserve all prior rows."""
import json,os,secrets,sys
from pathlib import Path
import frappe
from frappe.permissions import add_user_permission,add_permission,update_permission_property
from frappe.utils.password import update_password
from b08_distinct_concurrency_fixture import capture_tables,compare_tables,preserved,write_private
from b10_issue_fixture import TABLES
P=Path('/tmp/b08-private/b15-plan')
EXTRA=['Production Plan','Production Plan Item','Project','Project User','Document Naming Rule','Document Naming Rule Condition','Custom Field','Property Setter']
def prepare():
 assert not (P/'access.json').exists()
 if (P/'before.json').exists():before=json.loads((P/'before.json').read_text());assert preserved(compare_tables(before))
 else:before=capture_tables(TABLES+EXTRA);write_private(P/'before.json',before)
 old_info=json.loads(Path('/tmp/b08-private/b13-mobile/access.json').read_text());old=frappe.get_doc('Work Order',old_info['cases']['ui']['order']);prefix='b15-plan-'+frappe.generate_hash(length=8)
 a={'site':frappe.local.site,'base_url':'http://127.0.0.1:18090','prefix':prefix,'company':old.company,'team':old.production_team,'actors':{}}
 item=frappe.copy_doc(frappe.get_doc('Item',old.production_item));item.item_code=prefix+'-fg';item.item_name=prefix+'-成品';item.default_bom=None
 for row in item.item_defaults:row.default_bom=None
 item.insert();bom=frappe.copy_doc(frappe.get_doc('BOM',old.bom_no));bom.item=item.name;bom.docstatus=0;bom.insert().submit()
 project=frappe.get_doc({'doctype':'Project','project_name':prefix+'-装配分组','company':old.company}).insert()
 plan=frappe.get_doc({'doctype':'Production Plan','company':old.company,'project':project.name,'po_items':[{'item_code':item.name,'bom_no':bom.name,'planned_qty':qty,'planned_start_date':frappe.utils.add_days(frappe.utils.nowdate(),i),'warehouse':old.fg_warehouse,'stock_uom':item.stock_uom}for i,qty in enumerate([3,4,5])]}).insert();plan.submit()
 role=frappe.get_doc({'doctype':'Role','role_name':prefix+'-计划发起','desk_access':1}).insert().name
 for dt in ['Production Plan','Project']:
  add_permission(dt,role,ptype='read')
  for perm in ['write','create']:update_permission_property(dt,role,0,perm,1)
 roles=[r.role for r in frappe.get_doc('User',old_info['actors']['editor']['user']).roles if r.role!='生产报工'];assert 'System Manager' not in roles
 for alias in ['operator','other']:
  user=frappe.get_doc({'doctype':'User','email':prefix+'-'+alias+'@example.invalid','first_name':'计划发起人' if alias=='operator' else '计划跨对象核查','language':'zh','time_zone':'Asia/Shanghai','user_type':'System User','send_welcome_email':0,'roles':[{'role':r}for r in roles+[role]]}).insert();password=secrets.token_urlsafe(24);update_password(user.name,password);a['actors'][alias]={'user':user.name,'password':password};add_user_permission('Company',old.company,user.name);add_user_permission('Department',old.production_team,user.name,applicable_for='Work Order')
 a.update({'plan':plan.name,'rows':[row.name for row in plan.po_items],'project':project.name,'item':item.name,'bom':bom.name,'role':role,'delivery':frappe.utils.add_days(frappe.utils.nowdate(),7)})
 write_private(P/'access.json',a);checks=compare_tables(before);assert preserved(checks),checks;frappe.db.commit();return {'prepared':True,'old_tables_unchanged':len(checks),'plan':plan.name,'rows':a['rows'],'new_custom_fields':0}
def audit():
 before=json.loads((P/'before.json').read_text());a=json.loads((P/'access.json').read_text());checks=compare_tables(before);assert preserved(checks),checks
 orders=frappe.get_all('Work Order',filters={'production_plan':['in',[a['plan']]+([a['concurrency_plan']]if a.get('concurrency_plan')else[])]},fields=['name','qty','docstatus','workflow_state','production_plan_item','project','production_item'])
 for order in orders:assert order.docstatus==0 and order.workflow_state=='草稿';assert not frappe.db.exists('Job Card',{'work_order':order.name});assert not frappe.db.exists('Stock Entry',{'work_order':order.name})
 return {'old_rows_unchanged':True,'retention':checks,'orders':orders,'versions':frappe.get_all('Version',filters={'ref_doctype':'Work Order','docname':['in',[x.name for x in orders]]},fields=['docname','data'])}
if __name__=='__main__':
 os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True);os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
 try:
  assert frappe.conf.b08_http_only;frappe.set_user('Administrator');assert sys.argv[1]in ['prepare','audit'];print(json.dumps(prepare()if sys.argv[1]=='prepare'else audit(),ensure_ascii=False,default=str))
 finally:frappe.db.rollback();frappe.destroy()
