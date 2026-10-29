"""B07 original tests only, retained test site and complete fixture rollback."""
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
    assert frappe.conf.allow_tests and not frappe.db.exists("Workflow", {"document_type": "Work Order"})
    frappe.flags.in_test = True
    frappe.flags.skip_test_records = True
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment", "BOM", "BOM Item", "BOM Operation", "BOM Explosion Item"]
    def snapshot():
        return {dt: hashlib.sha256(frappe.as_json(frappe.get_all(dt, fields=["*"], order_by="name", limit_page_length=0)).encode()).hexdigest() for dt in tables}
    before = snapshot()
    prefix = "erpnext.manufacturing.doctype.work_order.test_work_order."
    names = [n if n.startswith("erpnext.") else prefix + n for n in sys.argv[1:]] or [prefix + "TestWorkOrderMaterials", prefix + "TestWorkOrderMaterialHistory"]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    frappe.db.rollback()
    assert snapshot() == before
    print(json.dumps({"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "old_tables_unchanged": len(tables)}))
finally:
    frappe.db.rollback()
    frappe.destroy()
sys.exit(0 if result.wasSuccessful() else 1)
