import os,json
import frappe
os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');pairs=frappe.get_all('Job Card',filters={'amended_from':['is','set'],'report_request_id':['is','set']},fields=['name','amended_from','work_order','docstatus','total_completed_qty','process_loss_qty'],limit_page_length=5);print(json.dumps({'existing_correction_pairs':pairs},ensure_ascii=False))
finally:frappe.db.rollback();frappe.destroy()
