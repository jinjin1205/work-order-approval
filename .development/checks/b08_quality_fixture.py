"""Only the new native-quality fixture: one report, a native QA role and one parent share.

Credentials and raw rows stay in the existing private mount; no customer roles change.
"""
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

import frappe
from frappe.permissions import add_permission, add_user_permission, update_permission_property
from frappe.utils.password import update_password

os.umask(0o077)
os.chdir("sites")
p = Path("/tmp/b08-private")
f = p / "b08-quality-ui.json"
a = json.loads(f.read_text())
assert a["site"] == "xgd-b08-http.localhost"
frappe.init(site=a["site"])
frappe.connect()


def row():
    return dict(frappe.get_all("Job Card", filters={"name": a["report"]}, fields=["*"])[0])


try:
    assert frappe.conf.b08_http_only
    frappe.set_user("Administrator")
    mode = sys.argv[1]
    if mode == "prepare":
        assert not a.get("report"), "Do not replay an already confirmed report"
        from erpnext.manufacturing.doctype.job_card.job_card import preview_production_report_time, confirm_production_report
        order = frappe.get_doc("Work Order", a["order"])
        assert order.workflow_state == "已批准"
        assert not frappe.db.exists("Job Card", {"work_order": order.name, "report_request_id": ["is", "set"]})
        args = dict(work_order=order.name, operation_id=order.operations[0].name,
            from_time="2026-10-29 09:00:00", to_time="2026-10-29 10:00:00", good_quantity=1, bad_quantity=1)
        frappe.set_user(a["actors"]["reporter"]["user"])
        preview = preview_production_report_time(**args)
        report = confirm_production_report(**args, request_id=frappe.generate_hash(length=32), context_fingerprint=preview["context_fingerprint"])
        a["report"] = report["name"]
        frappe.set_user("Administrator")
        role = frappe.get_doc({"doctype": "Role", "role_name": a["actors"]["reporter"]["user"].split("@")[0] + "-qa-select", "desk_access": 1}).insert().name
        for dt in ("Job Card", "Work Order", "Company", "Item", "User"):
            add_permission(dt, role, ptype="select")
            update_permission_property(dt, role, 0, "read", 0)
        update_permission_property("Item", role, 0, "read", 1)
        update_permission_property("Company", role, 0, "read", 1)
        user = a["actors"]["reporter"]["user"].replace("-reporter@", "-quality@")
        qa = frappe.get_doc({"doctype": "User", "email": user, "first_name": "原生质检验收员", "language": "zh",
            "time_zone": "Asia/Shanghai", "send_welcome_email": 0, "user_type": "System User",
            "roles": [{"role": r} for r in ("Quality Manager", role)]}).insert()
        password = secrets.token_urlsafe(24)
        update_password(user, password)
        qa.reload()
        qa.api_key, qa.api_secret = frappe.generate_hash(length=15), frappe.generate_hash(length=32)
        qa.save()
        add_user_permission("Company", a["company"], user)
        add_user_permission("Department", a["department"], user, applicable_for="Work Order")
        add_user_permission("Item", order.production_item, user)
        frappe.share.add("Job Card", a["report"], user, read=1, write=0, notify=0)
        a["actors"]["quality"] = {"user": user, "password": password, "api_key": qa.api_key, "api_secret": qa.get_password("api_secret")}
        foreign = frappe.get_all("Job Card", filters={"name": ["!=", a["report"]], "report_request_id": ["is", "set"], "docstatus": 1}, pluck="name")
        assert foreign
        a["foreign_report"] = foreign[0]
        frappe.set_user(user)
        assert not set(frappe.get_roles()) & {"System Manager", "Manufacturing Manager", "生产报工"}
        assert frappe.has_permission("Job Card", "read", doc=frappe.get_doc("Job Card", a["report"]), throw=False)
        assert not frappe.has_permission("Job Card", "read", doc=frappe.get_doc("Job Card", a["foreign_report"]), throw=False)
        a["image"] = str(p / "b08-quality-upload.png")
        from PIL import Image
        Image.frombytes("L", (32, 1), hashlib.sha256(a["report"].encode()).digest()).save(a["image"], format="PNG")
        (p / "b08-quality-report-before.json").write_text(json.dumps(row(), ensure_ascii=False, indent=2, default=str))
        a["image_sha256"] = hashlib.sha256(Path(a["image"]).read_bytes()).hexdigest()
        f.write_text(json.dumps(a, ensure_ascii=False, indent=2))
        frappe.db.commit()
        print(json.dumps({"new_report": 1, "good": 1, "bad": 1, "native_quality_user": 1, "parent_read_share_only": True, "foreign_denied": True, "no_new_fields": True, "secrets_printed": False}))
    elif mode == "configure-item":
        user = a["actors"]["quality"]["user"]
        role = a["actors"]["reporter"]["user"].split("@")[0] + "-qa-select"
        assert role.startswith("b06-task-") and role in frappe.get_roles(user)
        update_permission_property("Item", role, 0, "read", 1)
        update_permission_property("Company", role, 0, "read", 1)
        add_user_permission("Item", frappe.db.get_value("Work Order", a["order"], "production_item"), user)
        frappe.clear_cache(user=user)
        frappe.db.commit()
        print(json.dumps({"new_fixture_item_fetch_read_scoped_to_one_item": True, "old_roles_unchanged": True}))
    elif mode == "checkpoint":
        target = p / "b08-quality-report-checkpoint.json"
        assert not target.exists(), "Do not overwrite the pre-inspection baseline"
        before = json.loads((p / "b08-quality-report-before.json").read_text())
        after = json.loads(json.dumps(row(), default=str))
        changed = [key for key in before if before[key] != after[key]]
        assert not set(changed) - {"_seen"}, changed
        target.write_text(json.dumps(after, ensure_ascii=False, indent=2))
        print(json.dumps({"view_only_changed_fields": changed, "business_and_modified_unchanged": True}))
    elif mode == "describe":
        inspections = frappe.get_all("Quality Inspection", filters={"reference_type": "Job Card", "reference_name": a["report"]}, pluck="name")
        assert len(inspections) == 1
        a["inspection"] = inspections[0]
        files = frappe.get_all("File", filters={"attached_to_doctype": "Quality Inspection", "attached_to_name": a["inspection"]}, pluck="name")
        assert len(files) == 1
        a["image_file"] = files[0]
        a["file_url"] = frappe.db.get_value("File", files[0], "file_url")
        a["other_company"] = frappe.db.get_value("Company", {"name": ["!=", a["company"]]}, "name")
        assert a["other_company"]
        f.write_text(json.dumps(a, ensure_ascii=False, indent=2))
        print(json.dumps({"submitted_native_inspection": 1, "private_image": 1, "private_ids_recorded": True}))
    elif mode == "revoke":
        frappe.share.remove("Job Card", a["report"], a["actors"]["quality"]["user"])
        frappe.db.commit()
        print(json.dumps({"fixture_parent_share_revoked": True}))
    else:
        assert mode == "audit"
        old = json.loads((p / "b08-quality-before.json").read_text())
        additions = {}
        for dt, base in old.items():
            current = {r.name: hashlib.sha256(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
                for r in frappe.get_all(dt, fields=base["columns"], limit_page_length=0)}
            changed = [name for name, digest in base["rows"].items() if current.get(name) != digest]
            assert not changed, (dt, changed)
            additions[dt] = len(set(current) - set(base["rows"]))
        before = json.loads((p / "b08-quality-report-checkpoint.json").read_text())
        after = json.loads(json.dumps(row(), default=str))
        assert before == after, [key for key in before if before[key] != after[key]]
        assert frappe.db.count("Job Card", {"work_order": a["order"], "report_request_id": ["is", "set"]}) == 1
        assert not frappe.db.exists("Stock Entry", {"work_order": a["order"]})
        inspections = frappe.get_all("Quality Inspection", filters={"reference_type": "Job Card", "reference_name": a["report"]}, fields=["name", "docstatus", "status"])
        assert len(inspections) == 1 and inspections[0].docstatus == 1 and inspections[0].status == "Rejected"
        files = frappe.get_all("File", filters={"attached_to_doctype": "Quality Inspection", "attached_to_name": inspections[0].name}, pluck="name")
        assert len(files) == 1
        image = frappe.get_doc("File", files[0])
        assert image.is_private and hashlib.sha256(Path(image.get_full_path()).read_bytes()).hexdigest() == a["image_sha256"]
        print(json.dumps({"old_tables_unchanged": len(old), "new_rows": additions, "report_entire_row_unchanged_since_pre_inspection": True,
            "reports": 1, "good": 1, "bad": 1, "inventory": 0, "submitted_rejected_inspection": 1, "private_image_binary_unchanged": True}))
finally:
    frappe.db.rollback()
    frappe.destroy()
