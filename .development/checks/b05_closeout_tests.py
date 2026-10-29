"""Run the bounded timer/closeout tests on the retained rollback-only site."""
import hashlib
import json
import os
import sys
import unittest
import frappe
os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
try:
    assert frappe.conf.get("allow_tests")
    assert not frappe.db.exists("Workflow", {"document_type": "Work Order"})
    frappe.flags.in_test = True
    frappe.flags.skip_test_records = True
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment"]
    def snapshot():
        return {dt: hashlib.sha256(frappe.as_json(frappe.get_all(dt, fields=["*"], order_by="name", limit_page_length=0)).encode()).hexdigest() for dt in tables}
    before = snapshot()
    prefix = "erpnext.manufacturing.doctype.work_order.test_work_order."
    names = [name if name.startswith("erpnext.") else prefix + name for name in sys.argv[1:]] or [prefix + "TestWorkOrderCloseout"]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    frappe.db.rollback()
    assert before == snapshot(), "Existing eleven-table snapshot changed"
    print(json.dumps({"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "old_tables_unchanged": len(tables)}))
finally:
    frappe.db.rollback()
    frappe.destroy()
sys.exit(0 if result.wasSuccessful() else 1)
