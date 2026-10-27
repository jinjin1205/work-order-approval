"""R05 limited access/concurrency fixtures. Run only after root review/DB slot approval.

Exec inside the existing r05.localhost console. Native factories and Document APIs
only. No existing fixture is deleted or overwritten. Credentials are separate 0600.
"""
import json
import os
import secrets
import traceback
from datetime import datetime, timezone
from pathlib import Path

import frappe
from frappe.utils import add_to_date, now
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from frappe.core.doctype.user.user import generate_keys

PREFIX = "R05F-A"
BASE = Path("/home/frappe/frappe-bench/sites")
OUTPUT = BASE / "r05f-access-setup.json"
SECRET = BASE / "r05f-access-secrets.json"
report = {"prefix": PREFIX, "site": frappe.local.site,
          "started_utc": datetime.now(timezone.utc).isoformat(), "fixtures": {}, "users": {}}
if frappe.local.site != "r05.localhost" or OUTPUT.exists() or SECRET.exists():
    raise RuntimeError("Wrong site or retained output exists; do not overwrite")
if frappe.get_all("Item", filters={"name": ["like", PREFIX + "%"]}, limit=1):
    raise RuntimeError("Synthetic prefix exists; stop rather than reuse retained facts")

# Reuse the existing, already executed native fixture builders without executing
# their main program. get_all here is setup/inspection, never authorization evidence.
helpers = {}
exec(Path("/eval/r02_probe.py").read_text().split("\nif OUTPUT.exists():", 1)[0], helpers)
helpers["PREFIX"] = PREFIX
old_settings = {k: frappe.db.get_single_value("Manufacturing Settings", k) for k in helpers["SETTINGS"]}
credentials = {"site": "r05.localhost", "base_url": "http://127.0.0.1:18085", "users": {}}
try:
    frappe.db.set_single_value("Manufacturing Settings", dict(helpers["SETTINGS"]))
    for label in ["ALL", "DEPT", "PERSON", "B", "CONC2", "CONC1", "SPLIT1", "RETRY", "DELETE", "UI"]:
        case = {"case": label, "steps": []}
        wo, rm, fg = helpers["build_case"](case, label, 0.5, 1)
        transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
        transfer.submit()
        names = frappe.get_all("Job Card", filters={"work_order": wo.name}, pluck="name")
        if len(names) != 1:
            raise RuntimeError("Expected one native Job Card in new fixture")
        card = frappe.get_doc("Job Card", names[0])
        mapping = {"work_order": wo.name, "job_card": card.name, "operation": card.operation,
                   "stock_entry": transfer.name, "raw_item": rm, "finished_item": fg}
        if label in ["CONC2", "CONC1", "SPLIT1", "RETRY"]:
            # Native whole-card effective8 plus a separate draft2: no draft quantity
            # is represented as an already effective project report.
            card.for_quantity = 8
            start = now()
            card.append("time_logs", {"from_time": start,
                        "to_time": add_to_date(start, minutes=1), "completed_qty": 8})
            card.submit()
            pending = frappe.copy_doc(card)
            pending.docstatus = 0
            pending.for_quantity = 1 if label == "SPLIT1" else 2
            pending.set("time_logs", [])
            pending.total_completed_qty = 0
            pending.process_loss_qty = 0
            pending.insert()
            mapping["effective_eight_card"] = card.name
            mapping["job_card"] = pending.name
            if label == "SPLIT1":
                second_pending = frappe.copy_doc(pending)
                second_pending.insert()
                mapping["second_pending_card"] = second_pending.name
        if label == "DELETE":
            start = now()
            card.append("time_logs", {"from_time": start,
                        "to_time": add_to_date(start, minutes=1), "completed_qty": 10})
            card.remarks = "R05 synthetic delete probe; retained snapshot before any cancel/delete"
            card.submit()
        if label in ["DEPT", "B"]:
            draft = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
            draft.insert()
            mapping["stock_draft"] = draft.name
        mapping["initial"] = helpers["snapshot"](wo, rm, fg)
        report["fixtures"][label] = mapping

    roles = {"a": ["Manufacturing User"], "b": ["Manufacturing User"],
             "outside": ["Manufacturing User"], "stock": ["Stock User"], "none": []}
    access = {
        "a": [k for k in report["fixtures"] if k != "B"],
        "b": ["ALL", "DEPT", "CONC2", "CONC1", "SPLIT1", "RETRY"],
        "outside": ["ALL", "B"], "stock": ["DEPT"], "none": [],
    }
    for key, assigned_roles in roles.items():
        email = f"r05f-a-{key}@example.invalid"
        if frappe.db.exists("User", email):
            raise RuntimeError("Synthetic user already exists; stop")
        password = secrets.token_urlsafe(24)
        user = frappe.get_doc({"doctype": "User", "email": email,
            "first_name": f"R05F A {key}", "enabled": 1, "user_type": "System User",
            "send_welcome_email": 0, "new_password": password,
            "roles": [{"role": role} for role in assigned_roles]})
        user.insert()
        keys = generate_keys(email)
        user.reload()
        credentials["users"][key] = {"email": email, "password": password,
                                    "api_key": user.api_key, "api_secret": keys["api_secret"]}
        permission_ids = []
        for label in access[key]:
            permission = frappe.get_doc({"doctype": "User Permission", "user": email,
                "allow": "Work Order", "for_value": report["fixtures"][label]["work_order"],
                "apply_to_all_doctypes": 1}).insert()
            permission_ids.append(permission.name)
        frappe.clear_cache(user=email)
        report["users"][key] = {"email": email, "roles": frappe.get_roles(email),
                                "allowed_labels": access[key], "user_permissions": permission_ids}
    # Minimal synthetic employee for the native Start Job UI. Employee.on_update
    # adds its native Employee role to linked user a; record that explicitly.
    employee = frappe.get_doc({"doctype": "Employee", "naming_series": "HR-EMP-",
        "first_name": "R05F A synthetic worker", "company": helpers["COMPANY"],
        "status": "Active", "gender": "Other", "date_of_birth": "1990-01-01",
        "date_of_joining": "2026-01-01", "user_id": credentials["users"]["a"]["email"],
        "create_user_permission": 0}).insert()
    ui_card = frappe.get_doc("Job Card", report["fixtures"]["UI"]["job_card"])
    ui_card.append("employee", {"employee": employee.name})
    ui_card.save()
    report["fixtures"]["UI"]["employee"] = employee.name
    report["fixtures"]["UI"]["initial"] = helpers["snapshot"](
        frappe.get_doc("Work Order", ui_card.work_order),
        report["fixtures"]["UI"]["raw_item"], report["fixtures"]["UI"]["finished_item"])
    report["users"]["a"]["roles"] = frappe.get_roles(credentials["users"]["a"]["email"])
    report["users"]["a"]["employee_mapping"] = employee.name
    report["permission_mapping"] = "Explicit Work Order User Permissions; ALL/DEPT/PERSON are fixture labels. No automatic department/assignee policy was implemented."
    frappe.db.commit()
    report["transaction"] = "committed"
    # Secrets never enter report/stdout; mode is established before content write.
    with os.fdopen(os.open(SECRET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
        json.dump(credentials, f, ensure_ascii=False, indent=2)
except Exception:
    frappe.db.rollback()
    report["transaction"] = "rolled_back unless preceding explicit commit already completed"
    report["error"] = traceback.format_exc()
    raise
finally:
    frappe.db.rollback()
    frappe.db.set_single_value("Manufacturing Settings", dict(old_settings))
    frappe.db.commit()
    report["settings_restored"] = all(frappe.db.get_single_value("Manufacturing Settings", k) == v for k, v in old_settings.items())
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    with OUTPUT.open("x") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({"output": str(OUTPUT), "transaction": report.get("transaction"),
                      "settings_restored": report["settings_restored"], "has_error": "error" in report}))
