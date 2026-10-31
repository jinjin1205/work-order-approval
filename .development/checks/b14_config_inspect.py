import os,json,frappe
os.chdir('sites');frappe.init(site='xgd-test.localhost');frappe.connect()
try:
 frappe.set_user('Administrator');print(json.dumps({'companies':frappe.get_all('Company',pluck='name'),'naming_rules':frappe.get_all('Document Naming Rule',fields=['name','document_type','prefix','disabled']),'permission_roles':frappe.get_meta('User Permission').get('permissions')},ensure_ascii=False,default=str))
finally:frappe.db.rollback();frappe.destroy()
