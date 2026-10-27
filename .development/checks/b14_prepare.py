"""Install only B14's role and native link-select permissions on the isolated test site."""
import json
import os

import frappe
from frappe.permissions import add_permission

os.chdir("sites")
frappe.init(site="xgd-test.localhost")
frappe.connect()
try:
    assert frappe.conf.allow_tests
    assert not frappe.db.exists("Workflow", {"document_type": "Work Order"})
    frappe.set_user("Administrator")
    if not frappe.db.exists("Role", "生产配置管理员"):
        frappe.get_doc({"doctype": "Role", "role_name": "生产配置管理员", "desk_access": 1}).insert()
    for doctype in ("Company", "Operation"):
        add_permission(doctype, "生产配置管理员", ptype="select")
    frappe.db.commit()
    print(json.dumps({"site": frappe.local.site, "role": "生产配置管理员", "link_select_only": ["Company", "Operation"], "workflow_activated": False}, ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
