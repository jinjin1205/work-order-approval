"""New read/export identities; reuse prior business facts without replaying them."""
import json,os,secrets,sys
from pathlib import Path
import frappe
from frappe.permissions import add_permission,update_permission_property,add_user_permission
from frappe.utils.password import update_password
from b08_distinct_concurrency_fixture import capture_tables,compare_tables,preserved,write_private,digest
from b10_issue_fixture import TABLES
P=Path('/tmp/b08-private/b16-query')
EXTRA=['Report','Custom Role','Custom Field','Property Setter','Document Naming Rule','Document Naming Rule Condition']
def verify_retention(before):
 checks=compare_tables(before);exceptions=[]
 for table,counts in checks.items():
  assert not counts['missing'],(table,counts)
  if not counts['changed']:continue
  assert table=='Work Order' and counts['changed']==1,(table,counts)
  a=json.loads((P/'access.json').read_text());name='[本地样例编号已移除]';row=frappe.get_all(table,filters={'name':name},fields=before[table]['columns'])[0];seen=json.loads(row['_seen']);actor=a['actors']['reader']['user'];assert actor in seen
  candidate=dict(row);candidate['_seen']=json.dumps([user for user in seen if user!=actor]);assert digest(candidate)==before[table]['rows'][name], 'Other old fields changed; do not bless the difference'
  exceptions.append({'doctype':table,'name':name,'field':'_seen','evidence':'Native getdoc add_seen; removing only the new reader exactly matches the original whole-row hash'})
 return checks,exceptions

def prepare():
 assert not (P/'access.json').exists()
 if (P/'before.json').exists():before=json.loads((P/'before.json').read_text());assert preserved(compare_tables(before))
 else:before=capture_tables(TABLES+EXTRA);write_private(P/'before.json',before)
 prefix='b16-query-'+frappe.generate_hash(length=8);orders=['[本地样例编号已移除]','[本地样例编号已移除]','[本地样例编号已移除]','[本地样例编号已移除]'];source=frappe.get_doc('Work Order',orders[0]);a={'site':frappe.local.site,'base_url':'http://127.0.0.1:18090','prefix':prefix,'company':source.company,'orders':orders,'restricted_order':'[本地样例编号已移除]','actors':{}}
 roles={}
 for kind in ['read','export']:
  role=frappe.get_doc({'doctype':'Role','role_name':prefix+'-'+kind,'desk_access':1}).insert().name;roles[kind]=role
  for dt in ['Work Order','Job Card','Stock Entry']:
   add_permission(dt,role,ptype='read')
   for ptype in ['report','export']:update_permission_property(dt,role,0,ptype,int(ptype=='report' or kind=='export'))
  for dt in ['Company','Department','Item','Warehouse','BOM','Operation','Workstation','Fiscal Year']:
   add_permission(dt,role,ptype='read');update_permission_property(dt,role,0,'export',0)
 for report in ['Work Order Consumed Materials','Job Card Summary']:
  assert not frappe.db.exists('Custom Role',{'report':report}), 'Existing role override must be reviewed, not replaced'
  original=frappe.get_doc('Report',report);frappe.get_doc({'doctype':'Custom Role','report':report,'roles':[{'role':row.role}for row in original.roles]+[{'role':role}for role in roles.values()]}).insert()
 for alias,kind in [('reader','export'),('noexport','read'),('restricted','export')]:
  user=frappe.get_doc({'doctype':'User','email':prefix+'-'+alias+'@example.invalid','first_name':'核对查询-'+alias,'language':'zh','time_zone':'Asia/Shanghai','user_type':'System User','send_welcome_email':0,'roles':[{'role':roles[kind]}]}).insert();password=secrets.token_urlsafe(24);update_password(user.name,password);user.reload();user.api_key=frappe.generate_hash(length=15);user.api_secret=frappe.generate_hash(length=32);user.save();a['actors'][alias]={'user':user.name,'password':password,'api_key':user.api_key,'api_secret':user.get_password('api_secret')};add_user_permission('Company',source.company,user.name)
  scope=orders if alias!='restricted'else [a['restricted_order']]
  for name in scope:add_user_permission('Work Order',name,user.name)
  for team in {frappe.db.get_value('Work Order',name,'production_team')for name in scope}:add_user_permission('Department',team,user.name,applicable_for='Work Order')
 a['roles']=roles;write_private(P/'access.json',a);checks=compare_tables(before);assert preserved(checks),checks;frappe.db.commit();return {'prepared':True,'old_tables_unchanged':len(checks),'new_business_docs':0,'new_fields':0,'orders':orders}
def audit():
 a=json.loads((P/'access.json').read_text());checks,exceptions=verify_retention(json.loads((P/'before.json').read_text()))
 result={'old_rows_unchanged':not exceptions,'old_business_fields_unchanged':True,'native_seen_changes':exceptions,'retention':checks,'orders':[]}
 for name in a['orders']:
  doc=frappe.get_doc('Work Order',name);result['orders'].append({'name':name,'qty':doc.qty,'produced_qty':doc.produced_qty,'stock_uom':doc.stock_uom,'workflow_state':doc.workflow_state,'status':doc.status,'items':[{'item':x.item_code,'unit':x.stock_uom,'required':x.required_qty,'issued':x.transferred_qty,'returned':x.returned_qty,'consumed':x.consumed_qty}for x in doc.required_items], 'reports':frappe.get_all('Job Card',filters={'work_order':name,'report_request_id':['is','set']},fields=['name','docstatus','total_completed_qty','process_loss_qty','report_effective_seconds','amended_from','correction_reason']), 'stock':frappe.get_all('Stock Entry',filters={'work_order':name},fields=['name','docstatus','purpose','is_return','source_stock_entry'])})
 return result
if __name__=='__main__':
 os.umask(0o077);P.mkdir(mode=0o700,exist_ok=True);os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
 try:
  assert frappe.conf.b08_http_only;frappe.set_user('Administrator');assert sys.argv[1]in ['prepare','audit'];print(json.dumps(prepare()if sys.argv[1]=='prepare'else audit(),ensure_ascii=False,default=str))
 finally:frappe.db.rollback();frappe.destroy()
