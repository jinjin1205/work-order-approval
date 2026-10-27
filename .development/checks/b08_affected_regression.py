"""Only original approval/task/timer cases affected by the B08 entry changes."""
import os
import sys
import unittest

import frappe

os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
try:
    assert frappe.conf.get("allow_tests")
    frappe.flags.in_test = True
    frappe.flags.skip_test_records = True
    names = [
        "erpnext.manufacturing.doctype.job_card.test_job_card.TestJobCardExecutionApproval.test_approved_task_and_timer_allowed",
        "erpnext.manufacturing.doctype.job_card.test_job_card.TestJobCardExecutionApproval.test_pending_manual_job_card_denied",
        "erpnext.manufacturing.doctype.work_order.test_work_order.TestWorkOrderApproval.test_normal_two_stage_workflow",
    ]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
finally:
    frappe.db.rollback()
    frappe.destroy()
sys.exit(0 if result.wasSuccessful() else 1)
