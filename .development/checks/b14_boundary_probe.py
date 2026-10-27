"""Native B14 boundary probes, rolled back; no credentials or fixture records printed."""
import json
import os

import frappe
from erpnext.manufacturing.doctype.production_time_rule.test_production_time_rule import TestProductionTimeRule

os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
fixture = TestProductionTimeRule()
try:
    fixture.setUp()
    foreign = fixture.make_rule(company=fixture.other_company()).insert()
    frappe.set_user(fixture.user)
    foreign.company = fixture.company
    try:
        foreign.save()
        print(json.dumps({"case": "foreign_company_reparent_to_authorized", "saved": True}))
    except frappe.PermissionError:
        print(json.dumps({"case": "foreign_company_reparent_to_authorized", "saved": False, "error": "PermissionError"}))
    for value in (None, ""):
        doc = fixture.make_rule(company=value)
        try:
            doc.insert()
            print(json.dumps({"case": "company_missing", "input": value, "saved": True,
                "native_default_matches_authorized_company": doc.company == fixture.company}))
        except frappe.ValidationError:
            print(json.dumps({"case": "company_missing", "input": value, "saved": False, "error": "ValidationError"}))
finally:
    fixture.doCleanups()
    frappe.destroy()
