"""New narrow initiating user and independent draft for B08 configuration UI acceptance."""
import json
import os
import secrets
from pathlib import Path

import frappe
from frappe.permissions import add_user_permission
from frappe.utils.password import update_password

os.umask(0o077)
os.chdir("sites")
private = Path("/tmp/b08-private")
target = private / "metrics-config-access.json"
assert not target.exists(), "Inspect the existing configuration sample; do not recreate it"
source = json.loads((private / "fixture.json").read_text())
metrics = json.loads((private / "metrics-20261028.json").read_text())
assert source["site"] == metrics["site"] == "xgd-b08-http.localhost"
frappe.init(site=source["site"])
frappe.connect()
try:
    assert frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    original = frappe.get_doc("Work Order", source["order"])
    draft = frappe.get_doc("Work Order", metrics["orders"]["draft"]["order"])
    assert draft.docstatus == 0 and draft.workflow_state == "草稿"
    assert (draft.company, draft.production_team) == (original.company, original.production_team)
    initiator = frappe.get_doc("User", original.approval_requested_by)
    roles = [row.role for row in initiator.roles]
    assert "生产工单发起" in roles
    assert not set(roles) & {"System Manager", "Manufacturing Manager", "生产工单审核", "生产工单签批"}
    for doctype, value in (("Company", original.company), ("Department", original.production_team)):
        assert frappe.db.exists("User Permission", {"user": initiator.name, "allow": doctype, "for_value": value})

    user = "b08-metrics-config-" + frappe.generate_hash(length=10) + "@example.invalid"
    assert not frappe.db.exists("User", user)
    frappe.get_doc({"doctype": "User", "email": user, "first_name": "计价配置验收发起人",
                    "language": "zh", "enabled": 1, "send_welcome_email": 0,
                    "user_type": "System User", "roles": [{"role": role} for role in roles]}).insert()
    password = secrets.token_urlsafe(24)
    update_password(user, password)
    add_user_permission("Company", original.company, user)
    add_user_permission("Department", original.production_team, user, applicable_for="Work Order")

    frappe.set_user(user)
    order = frappe.copy_doc(draft)
    order.docstatus = 0
    order.status = "Draft"
    order.workflow_state = "草稿"
    for field in ("approval_requested_by", "approval_reviewed_by", "approval_note", "amended_from", "previous_work_order",
                  "actual_start_date", "actual_end_date"):
        order.set(field, None)
    for field in ("produced_qty", "material_transferred_for_manufacturing", "process_loss_qty",
                  "actual_operating_cost", "corrective_operation_cost", "lead_time"):
        order.set(field, 0)
    for row in order.operations:
        row.docstatus = 0
        row.status = "Pending"
        for field in ("completed_qty", "process_loss_qty", "actual_operation_time", "actual_operating_cost"):
            row.set(field, 0)
        row.actual_start_time = row.actual_end_time = None
        for field in ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency"):
            row.set(field, None)
    for row in order.required_items:
        row.docstatus = 0
        for field in ("transferred_qty", "consumed_qty", "returned_qty"):
            row.set(field, 0)
    order.insert()
    assert order.docstatus == 0 and order.workflow_state == "草稿"
    assert order.owner == user and order.approval_requested_by == user
    assert not frappe.db.exists("Job Card", {"work_order": order.name})
    assert not frappe.db.exists("Stock Entry", {"work_order": order.name})
    currency = frappe.db.get_value("Company", order.company, "default_currency")
    value = {"site": source["site"], "base_url": "http://127.0.0.1:18090", "user": user, "password": password,
             "order": order.name, "operation_id": order.operations[0].name, "company": order.company,
             "company_currency": currency, "roles": roles}
    with target.open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")
    target.chmod(0o600)
    frappe.db.commit()
    print(json.dumps({"new_narrow_initiator": True, "new_independent_draft": True,
                      "existing_accounts_unchanged": True, "reports_created": 0,
                      "stock_entries_created": 0, "secrets_printed": False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
