"""Align isolated upstream fixtures; never run against the development site."""
import json
import os

import frappe
from frappe.model.rename_doc import rename_doc, validate_rename

os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
try:
    assert frappe.conf.get("allow_tests"), "Only an explicitly enabled test site is allowed"
    frappe.set_user("Administrator")
    mappings = [
        ("Item Group", "parent_item_group", "所有物料群组", "All Item Groups"),
        ("Customer Group", "parent_customer_group", "所有客户群组", "All Customer Groups"),
        ("Supplier Group", "parent_supplier_group", "所有供应商组织", "All Supplier Groups"),
        ("Territory", "parent_territory", "所有的区域", "All Territories"),
        ("Department", "parent_department", "所有部门", "All Departments"),
        ("Sales Person", "parent_sales_person", "销售团队", "Sales Team"),
    ]
    result = []
    for doctype, parent_field, old, new in mappings:
        roots = frappe.get_all(doctype, filters={parent_field: ["is", "not set"]}, pluck="name")
        if roots == [new]:
            assert not frappe.db.exists(doctype, old)
            result.append({"doctype": doctype, "name": new, "status": "already prepared"})
            continue
        assert roots == [old], (doctype, roots)
        assert not frappe.db.exists(doctype, new), (doctype, new)
        if doctype == "Department":
            doc = frappe.get_doc(doctype, old)
            assert not doc.company
            # The upstream company-abbreviation hook cannot handle a company-less root.
            # Retain native permission, conflict and naming validation for this fixture only.
            validated = validate_rename(doctype, old, new, frappe.get_meta(doctype), merge=False, old_doc=doc)
            rename_doc(doctype, old, validated, validate=False, rebuild_search=False, show_alert=False)
        else:
            frappe.rename_doc(doctype, old, new, rebuild_search=False, show_alert=False)
        assert frappe.get_all(doctype, filters={parent_field: ["is", "not set"]}, pluck="name") == [new]
        assert not frappe.db.exists(doctype, old)
        assert not frappe.db.exists(doctype, {parent_field: old})
        result.append({"doctype": doctype, "old": old, "new": new})
    assert frappe.db.get_single_value("System Settings", "language") == "zh"
    frappe.db.commit()
    print(json.dumps({"site": frappe.local.site, "renamed": result, "language": "zh", "scope": "test fixtures only"}, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
