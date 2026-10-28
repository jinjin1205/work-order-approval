"""Create retained, isolated B08 history-path HTTP samples; never run attack requests.

Only setup and read-only preservation modes are provided. Credentials and raw IDs
stay under /tmp/b08-history-paths-private, with mode 0600. Run from the existing
B08 check container, whose working directory is the bench root.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import frappe
from frappe.core.doctype.user.user import generate_keys
from frappe.permissions import add_permission, add_user_permission, update_permission_property
from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
from erpnext.manufacturing.doctype.job_card.job_card import (
    confirm_production_report, correct_production_report, preview_production_report_time,
)

os.umask(0o077)
os.chdir("sites")
PRIVATE = Path("/tmp/b08-history-paths-private")
PRIVATE.mkdir(mode=0o700, exist_ok=True)
PRIVATE.chmod(0o700)
TARGET = PRIVATE / "fixture.json"
BASELINE = PRIVATE / "before.json"
TABLES = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card",
          "Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry",
          "Workflow Action", "Version", "Comment"]
SECURITY_TABLES = ["User", "Role", "Has Role", "User Permission", "Custom DocPerm"]


def digest(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False,
                                     default=str, separators=(",", ":")).encode()).hexdigest()


def write_private(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")
    path.chmod(0o600)


def capture(doctypes):
    result = {}
    for doctype in doctypes:
        columns = sorted(frappe.db.get_table_columns(doctype))
        rows = frappe.get_all(doctype, fields=columns, order_by="name", limit_page_length=0)
        result[doctype] = {"columns": columns, "rows": {r.name: digest(r) for r in rows}}
    return result


def compare(captured):
    result = {}
    for doctype, before in captured.items():
        rows = frappe.get_all(doctype, fields=before["columns"], order_by="name", limit_page_length=0)
        after = {r.name: digest(r) for r in rows}
        missing = sum(name not in after for name in before["rows"])
        changed = sum(name in after and value != after[name] for name, value in before["rows"].items())
        result[doctype] = {"old_rows": len(before["rows"]), "missing": missing,
                           "changed": changed, "new_rows": len(set(after) - set(before["rows"]))}
    return result


def unchanged(summary):
    return all(not item["missing"] and not item["changed"] for item in summary.values())


source = json.loads(Path("/tmp/b08-private/fixture.json").read_text())
assert source["site"] == "xgd-b08-http.localhost"
frappe.init(site=source["site"])
frappe.connect()
try:
    assert frappe.conf.b08_http_only, "Only the dedicated retained synthetic site is allowed"
    frappe.set_user("Administrator")
    mode = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if mode == "exists":
        sample = json.loads(TARGET.read_text())
        kind, index = sys.argv[2], int(sys.argv[3])
        assert kind in ("operation", "time") and index in (0, 1, 2)
        doctype = "Work Order Operation" if kind == "operation" else "Job Card Time Log"
        names = sample["orders"]["disposable"]["operations"] if kind == "operation" else sample["disposable_logs"]
        assert names[index] in sample["authorized_disposable_children"][doctype]
        print(json.dumps({"doctype": doctype, "fixture_row_index": index,
                          "exists": bool(frappe.db.exists(doctype, names[index])),
                          "protected_cancelled_time_exists": bool(frappe.db.exists("Job Card Time Log", sample["cancelled_log"]))}))
    elif mode == "preserve":
        baseline = json.loads(BASELINE.read_text())
        summary = {"business": compare(baseline["tables"]), "security": compare(baseline["security_tables"])}
        summary["all_old_rows_unchanged"] = unchanged(summary["business"]) and unchanged(summary["security"])
        sample = json.loads(TARGET.read_text())
        summary["disposable_operation_rows_existing"] = [
            bool(frappe.db.exists("Work Order Operation", name))
            for name in sample["orders"]["disposable"]["operations"]]
        summary["disposable_time_rows_existing"] = [
            bool(frappe.db.exists("Job Card Time Log", name)) for name in sample["disposable_logs"]]
        summary["protected_cancelled_time_exists"] = bool(frappe.db.exists("Job Card Time Log", sample["cancelled_log"]))
        print(json.dumps(summary, ensure_ascii=False))
        assert summary["all_old_rows_unchanged"], "Old rows changed; inspect privately"
    else:
        assert mode == "setup" and not TARGET.exists(), "Do not replay an existing fixture"
        if BASELINE.exists():
            baseline = json.loads(BASELINE.read_text())
            assert unchanged(compare(baseline["tables"])) and unchanged(compare(baseline["security_tables"])), "Do not replace an earlier baseline"
        else:
            baseline = {"site": source["site"], "captured_at": str(frappe.utils.now_datetime()),
                        "hash": "sha256 canonical JSON of every captured original column",
                        "tables": capture(TABLES), "security_tables": capture(SECURITY_TABLES)}
            write_private(BASELINE, baseline)

        original = frappe.get_doc("Work Order", source["order"])
        assert original.qty == 10 and len(original.operations) == 3
        assert not any(original.get(f) for f in ("sales_order", "sales_order_item", "material_request",
                       "material_request_item", "production_plan", "production_plan_item", "production_plan_sub_assembly_item"))
        reviewer = original.approval_reviewed_by
        director = source["user"].replace("-report@", "-director@")
        assert "生产工单审核" in frappe.get_roles(reviewer) and "生产工单签批" in frappe.get_roles(director)
        prefix = "b08-history-" + frappe.generate_hash(length=10)
        role = prefix + "-限定验收"
        frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()
        permissions = {
            "Work Order": ("read", "create", "write", "submit", "delete"),
            "Job Card": ("read", "create", "write", "submit", "cancel", "delete"),
        }
        for doctype, allowed in permissions.items():
            add_permission(doctype, role, ptype="read")
            for permission in allowed:
                update_permission_property(doctype, role, 0, permission, 1)
        user = prefix + "@example.invalid"
        frappe.get_doc({"doctype": "User", "email": user, "first_name": "历史保护验收",
                       "enabled": 1, "send_welcome_email": 0, "language": "zh", "user_type": "System User",
                       "roles": [{"role": r} for r in ("生产工单发起", "生产报工", role)]}).insert()
        assert "System Manager" not in frappe.get_roles(user)
        employee = frappe.get_doc({"doctype": "Employee", "first_name": "历史保护验收", "gender": "Male",
                                  "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
                                  "company": original.company, "department": original.production_team,
                                  "status": "Active", "user_id": user, "create_user_permission": 0}).insert()
        add_user_permission("Company", original.company, user)
        add_user_permission("Department", original.production_team, user, applicable_for="Work Order")
        workstation = frappe.copy_doc(frappe.get_doc("Workstation", original.operations[0].workstation))
        workstation.workstation_name = prefix + "-工作中心"
        workstation.status = "Off"
        workstation.insert()

        orders = {}
        for label in ("history", "empty_card", "destination", "disposable"):
            frappe.set_user(user)
            order = frappe.copy_doc(original)
            order.docstatus = 0
            order.status = "Draft"
            order.workflow_state = "草稿"
            for field in ("approval_requested_by", "approval_reviewed_by", "approval_note", "amended_from",
                          "previous_work_order", "actual_start_date", "actual_end_date"):
                order.set(field, None)
            for field in ("produced_qty", "material_transferred_for_manufacturing", "process_loss_qty",
                          "actual_operating_cost", "corrective_operation_cost", "lead_time"):
                order.set(field, 0)
            for row in order.operations:
                row.docstatus = 0
                row.status = "Pending"
                row.workstation = workstation.name
                for field in ("completed_qty", "process_loss_qty", "actual_operation_time", "actual_operating_cost"):
                    row.set(field, 0)
                row.actual_start_time = row.actual_end_time = None
                for field in ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency"):
                    row.set(field, None)
                row.report_scope = "PERSON"
                row.report_employee = employee.name
                row.report_department = None
            for row in order.required_items:
                row.docstatus = 0
                for field in ("transferred_qty", "consumed_qty", "returned_qty"):
                    row.set(field, 0)
            order.insert(set_name=prefix + "-" + label)
            orders[label] = order

        frappe.set_user("Administrator")
        for order in orders.values():
            add_user_permission("Work Order", order.name, user)
        for label in ("history", "empty_card"):
            order = orders[label]
            for actor, action in ((user, "送审"), (reviewer, "审核通过"), (director, "签批通过")):
                frappe.set_user(actor)
                apply_production_approval(order.name, action, str(order.modified))
                order.reload()
            assert order.docstatus == 1 and order.workflow_state == "已批准"

        frappe.set_user(user)
        history = orders["history"]
        inputs = {"work_order": history.name, "operation_id": history.operations[0].name,
                  "from_time": "2026-11-09 09:00:00", "to_time": "2026-11-09 11:00:00",
                  "good_quantity": 2, "bad_quantity": 0, "shutdown_seconds": 0, "overtime_seconds": 0}
        preview = preview_production_report_time(**inputs)
        assert preview["metrics"]["source"]["wage_mode"] is None
        confirmed = confirm_production_report(**inputs, request_id=prefix + "-confirm",
                                               context_fingerprint=preview["context_fingerprint"])
        corrected = correct_production_report(confirmed["name"], prefix + "-correct", 1, 0, "合成验收：保留取消态原报工")
        cancelled = frappe.get_doc("Job Card", confirmed["name"])
        replacement = frappe.get_doc("Job Card", corrected["name"])
        assert cancelled.docstatus == 2 and replacement.docstatus == 1
        assert replacement.amended_from == cancelled.name and len(cancelled.time_logs) == 1
        empty_order = orders["empty_card"]
        plan_name = frappe.db.get_value("Job Card", {"work_order": empty_order.name,
                                                     "operation_id": empty_order.operations[0].name, "docstatus": 0}, "name")
        empty_card = frappe.get_doc("Job Card", plan_name)
        assert not empty_card.report_request_id and not empty_card.time_logs
        # Deliberately empty draft children: no person, quantity or time is asserted.
        for _ in range(3):
            empty_card.append("time_logs", {"completed_qty": 0})
        empty_card.save()
        assert not empty_card.total_completed_qty and not empty_card.total_time_in_mins
        assert all(not row.from_time and not row.to_time and not row.completed_qty for row in empty_card.time_logs)

        checks = []
        for doctype, name, perms in (
            ("Work Order Operation", history.operations[0].name, ("read", "write", "submit", "delete")),
            ("Job Card Time Log", cancelled.time_logs[0].name, ("read", "write", "delete")),
            ("Work Order", orders["destination"].name, ("read", "write", "delete")),
            ("Job Card", empty_card.name, ("read", "write", "delete")),
        ):
            doc = frappe.get_doc(doctype, name)
            for permission in perms:
                allowed = bool(doc.has_permission(permission))
                checks.append({"doctype": doctype, "permission": permission, "allowed": allowed})
                assert allowed, "Synthetic actor must have base permission before testing business guards"
        frappe.set_user("Administrator")
        value = {"site": source["site"], "base_url": "http://127.0.0.1:18090", "prefix": prefix,
                 "user": user, "role": role, "employee": employee.name, "keys": generate_keys(user),
                 "orders": {key: {"order": doc.name, "operations": [row.name for row in doc.operations]}
                            for key, doc in orders.items()},
                 "cancelled_card": cancelled.name, "cancelled_log": cancelled.time_logs[0].name,
                 "replacement_card": replacement.name, "empty_card": empty_card.name,
                 "disposable_logs": [row.name for row in empty_card.time_logs],
                 "alternate_operation": history.operations[1].operation,
                 "authorized_disposable_children": {
                     "Work Order Operation": [row.name for row in orders["disposable"].operations],
                     "Job Card Time Log": [row.name for row in empty_card.time_logs]},
                 "baseline_file": str(BASELINE)}
        retention = {"business": compare(baseline["tables"]), "security": compare(baseline["security_tables"])}
        assert unchanged(retention["business"]) and unchanged(retention["security"]), "Existing rows changed; rollback setup"
        assert all(not retention["business"][dt]["new_rows"] for dt in ("Stock Entry", "Stock Entry Detail", "Stock Ledger Entry"))
        write_private(TARGET, value)
        frappe.db.commit()
        print(json.dumps({"fixture_ready": True, "new_users": 1, "new_roles": 1, "new_orders": 4,
                          "approved_orders": 2, "new_confirmed_reports": 1, "retained_cancelled_reports": 1,
                          "empty_draft_time_rows": 3, "base_permissions": checks,
                          "old_rows_unchanged": True, "stock_rows_added": 0,
                          "negative_http_executed": False, "credentials_printed": False}, ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
