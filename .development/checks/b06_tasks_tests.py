"""B06 only: original test classes, retained site, rollback and table hashes."""
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
    tables = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment", "BOM", "BOM Item", "BOM Operation", "BOM Explosion Item"]
    if any("TestProductionNativeQuality" in name or "TestProductionReportLifecycle" in name for name in sys.argv[1:]):
        tables += ["Quality Inspection", "Quality Inspection Reading", "File"]
    if any("TestProductionMaterialIssue" in name or "TestProductionMaterialReturn" in name for name in sys.argv[1:]):
        tables += ["Bin", "GL Entry", "Repost Item Valuation", "Warehouse", "User", "User Permission", "Custom DocPerm", "Has Role"]
    def snapshot():
        return {dt: hashlib.sha256(frappe.as_json(frappe.get_all(dt, fields=["*"], order_by="name", limit_page_length=0)).encode()).hexdigest() for dt in tables}
    before = snapshot()
    names = sys.argv[1:] or ["erpnext.manufacturing.doctype.work_order.test_work_order.TestWorkOrderTaskAdjustments", "erpnext.manufacturing.doctype.job_card.test_job_card.TestProductionTaskPlans"]
    if any(name.startswith("erpnext.manufacturing.doctype.work_order.test_work_order.TestWorkOrder.test_") for name in names):
        # Minimal missing fixture for the explicitly selected upstream tests; no dependency initializer.
        from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrder
        native_setup = TestWorkOrder.setUp
        def setup_with_product_group(self):
            if not frappe.db.exists("Item Group", "Products"):
                frappe.get_doc({"doctype": "Item Group", "item_group_name": "Products", "parent_item_group": "All Item Groups"}).insert()
            native_setup(self)
        TestWorkOrder.setUp = setup_with_product_group
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    frappe.db.rollback()
    assert before == snapshot(), "Existing captured rows changed"
    print(json.dumps({"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "old_tables_unchanged": len(tables)}))
finally:
    frappe.db.rollback()
    frappe.destroy()
sys.exit(0 if result.wasSuccessful() else 1)
