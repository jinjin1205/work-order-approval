"""Read-only evidence of the retained HTTP fixture scope; never disclose credentials."""
import json, os
import frappe
os.chdir("sites")
for site in ("xgd-b19-http.localhost", "xgd-dev.localhost", "xgd-test.localhost"):
    frappe.init(site=site)
    frappe.connect()
    try:
        rows=frappe.get_all("Workflow", filters={"document_type":"Work Order"}, fields=["name","is_active"])
        print(json.dumps({"site":site,"http_only":bool(frappe.conf.get("b19_http_only")),"is_dedicated_http_database":frappe.conf.db_name=="xgd_b19_http","work_order_workflows":rows},ensure_ascii=False))
    finally:
        frappe.db.rollback()
        frappe.destroy()
