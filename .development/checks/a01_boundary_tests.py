import os
import sys
import unittest
import json
import frappe
from b08_distinct_concurrency_fixture import capture_tables, compare_tables, preserved
from b10_issue_fixture import TABLES

if __name__ == '__main__':
    os.chdir('sites'); frappe.init(site='xgd-test.localhost'); frappe.connect()
    try:
        assert frappe.conf.allow_tests and not frappe.db.exists('Workflow', {'document_type':'Work Order'})
        frappe.flags.in_test=True; frappe.flags.skip_test_records=True
        frappe.set_user('Administrator')
        before=capture_tables(TABLES+['Workflow','Workflow Document State','Workflow Transition','Custom Field'])
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or [
            'erpnext.manufacturing.test_production_ai.TestProductionAIBoundary']))
        frappe.set_user('Administrator'); frappe.db.rollback()
        retention=compare_tables(before); assert preserved(retention),retention
        print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),old_tables_unchanged=len(retention))))
    finally:
        frappe.db.rollback(); frappe.clear_cache(); frappe.destroy()
    sys.exit(0 if result.wasSuccessful() else 1)
