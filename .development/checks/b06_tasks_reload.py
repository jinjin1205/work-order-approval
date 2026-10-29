"""Reload only the new task-plan column on the two dedicated synthetic sites."""
import os
import sys
import frappe

os.chdir("sites")
site = sys.argv[1]
assert site in ("xgd-test.localhost", "xgd-b08-http.localhost")
frappe.init(site=site)
frappe.connect()
try:
    assert frappe.conf.allow_tests or frappe.conf.b08_http_only
    frappe.reload_doc("manufacturing", "doctype", "work_order_operation", force=True)
    frappe.clear_cache(doctype="Work Order Operation")
    frappe.clear_cache(doctype="Work Order")
    assert frappe.db.has_column("Work Order Operation", "report_plan_qty")
    assert frappe.get_meta("Work Order Operation").get_field("report_plan_qty").fieldtype == "Data"
    frappe.db.commit()
    print("B06 task-plan metadata ready on dedicated synthetic site")
finally:
    frappe.destroy()
