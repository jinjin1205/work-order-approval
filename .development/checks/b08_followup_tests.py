"""Run only B08-02/05 additions, retaining the original 14+1 evidence boundary."""
import os
import sys
import unittest
import frappe
os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
try:
    assert frappe.conf.get("allow_tests")
    assert not frappe.db.exists("Workflow", {"document_type":"Work Order"})
    frappe.flags.in_test = True
    frappe.flags.skip_test_records = True
    tables = ["Production Time Rule", "Production Time Period", "Employee", "User Permission"]
    before = {dt:frappe.as_json(frappe.get_all(dt, fields=["*"], order_by="name")) for dt in tables}
    prefix = "erpnext.manufacturing.doctype.job_card.test_job_card.TestProductionReportFollowup"
    names = [name if "." in name else prefix + "." + name for name in sys.argv[1:]] or [prefix]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    frappe.db.rollback()
    assert all(frappe.as_json(frappe.get_all(dt, fields=["*"], order_by="name")) == before[dt] for dt in tables)
    print("Existing rules, employees and User Permission rows unchanged after fixture rollback", flush=True)
finally:
    frappe.db.rollback()
    frappe.destroy()
sys.exit(0 if result.wasSuccessful() else 1)
