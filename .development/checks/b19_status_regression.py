"""Bounded status calculation checks; no saved documents or mocked business methods."""
import os
import sys
import unittest

import frappe


class TestStatusCalculation(unittest.TestCase):
    def order(self, **values):
        order = frappe.new_doc("Work Order")
        order.update(dict(docstatus=1, skip_transfer=1, qty=10, produced_qty=2))
        order.update(values)
        return order

    def test_partial_production_remains_in_process(self):
        self.assertEqual(self.order().get_status(), "In Process")

    def test_fractional_process_loss_can_complete(self):
        # Same inputs as the upstream TestWorkOrder regression, without its unrelated setUp.
        order = self.order(qty=11.4, produced_qty=11.2, process_loss_qty=0.2)
        self.assertEqual(order.get_status(), "Completed")

    def test_stopped_partial_production_stays_stopped(self):
        self.assertEqual(self.order(status="Stopped").get_status(), "Stopped")

    def test_closed_partial_production_stays_closed(self):
        self.assertEqual(self.order(status="Closed").get_status(), "Closed")


os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
try:
    assert frappe.conf.get("allow_tests"), "Only the isolated test site is allowed"
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestStatusCalculation)
    )
finally:
    frappe.db.rollback()
    frappe.destroy()
sys.exit(0 if result.wasSuccessful() else 1)
