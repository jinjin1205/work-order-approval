import os,json
import frappe
from frappe.translate import clear_cache
os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;clear_cache();frappe.local.lang='zh';values=[frappe._('docstatus'),frappe._('owner'),frappe._('ID',context='Label of name column in report')];assert values==['单据状态','创建人','编号'],values;print(json.dumps(values,ensure_ascii=False))
finally:frappe.db.rollback();frappe.destroy()
