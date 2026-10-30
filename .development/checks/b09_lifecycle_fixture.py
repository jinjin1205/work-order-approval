"""B09 synthetic case only; never consumes unrelated jobs or exports credentials."""
import hashlib
import json
import os
import sys
from io import BytesIO
from pathlib import Path

import frappe
from frappe.permissions import add_permission, update_permission_property

os.umask(0o077)
os.chdir("sites")
p = Path("/tmp/b08-private")
f = p / "b09-lifecycle-ui.json"
a = json.loads(f.read_text())
assert a["site"] == "xgd-b08-http.localhost"
frappe.init(site=a["site"])
frappe.connect()


def raw(dt, names):
    return json.loads(frappe.as_json(frappe.get_all(dt, filters={"name": ["in", names]}, fields=["*"], order_by="name", limit_page_length=0)))


def protected():
    cards = [a["report"], a["replacement"]]
    data = {"Job Card": raw("Job Card", cards), "Work Order": raw("Work Order", [a["order"]]),
        "Work Order Operation": raw("Work Order Operation", a["original_rows"]),
        "Quality Inspection": raw("Quality Inspection", [a["inspection"]]), "File": raw("File", [a["image_file"]])}
    for dt, parents in (("Job Card Time Log", cards), ("Quality Inspection Reading", [a["inspection"]])):
        data[dt] = raw(dt, frappe.get_all(dt, filters={"parent": ["in", parents]}, pluck="name"))
    image = frappe.get_doc("File", a["image_file"])
    data["image_sha256"] = hashlib.sha256(Path(image.get_full_path()).read_bytes()).hexdigest()
    return data


try:
    assert frappe.conf.b08_http_only
    mode = sys.argv[1]
    frappe.set_user("Administrator")
    if mode == "prepare":
        assert not a.get("report"), "No replay of committed fixture"
        from erpnext.manufacturing.doctype.job_card.job_card import preview_production_report_time, confirm_production_report, correct_production_report
        order = frappe.get_doc("Work Order", a["order"])
        assert order.workflow_state == "已批准"
        role = frappe.get_doc({"doctype": "Role", "role_name": a["actors"]["reporter"]["user"].split("@")[0] + "-lifecycle", "desk_access": 1}).insert().name
        add_permission("Job Card", role, ptype="read")
        for perm in ("cancel", "delete"):
            update_permission_property("Job Card", role, 0, perm, 1)
        frappe.get_doc("User", a["actors"]["reporter"]["user"]).add_roles(role, "Quality Manager")
        frappe.set_user(a["actors"]["reporter"]["user"])
        assert "System Manager" not in frappe.get_roles()
        assert not order.has_permission("write")
        args = dict(work_order=order.name, operation_id=order.operations[0].name,
            from_time="2026-10-30 09:00:00", to_time="2026-10-30 10:00:00", good_quantity=1, bad_quantity=1)
        preview = preview_production_report_time(**args)
        a["report"] = confirm_production_report(**args, request_id=frappe.generate_hash(length=32), context_fingerprint=preview["context_fingerprint"])["name"]
        card = frappe.get_doc("Job Card", a["report"])
        inspection = frappe.get_doc({"doctype": "Quality Inspection", "inspection_type": "In Process",
            "reference_type": "Job Card", "reference_name": card.name, "company": card.company,
            "item_code": card.production_item, "sample_size": 1, "inspected_by": frappe.session.user,
            "report_date": frappe.utils.nowdate(), "manual_inspection": 1, "status": "Rejected"}).insert()
        from PIL import Image
        buffer = BytesIO()
        Image.frombytes("L", (32, 1), hashlib.sha256(card.name.encode()).digest()).save(buffer, format="PNG")
        image = frappe.get_doc({"doctype": "File", "file_name": a["actors"]["reporter"]["user"].split("@")[0] + "-lifecycle.png",
            "content": buffer.getvalue(), "is_private": 1, "attached_to_doctype": "Quality Inspection", "attached_to_name": inspection.name}).insert()
        inspection.submit()
        inspection.cancel()
        a["inspection"], a["image_file"] = inspection.name, image.name
        a["replacement"] = correct_production_report(card.name, frappe.generate_hash(length=32), 1, 0, "B09合成验收：保留原报工并关联更正")["name"]
        assert frappe.db.get_value("Job Card", card.name, "docstatus") == 2
        assert frappe.db.get_value("Job Card", a["replacement"], "amended_from") == card.name
        frappe.set_user(a["actors"]["editor"]["user"])
        plan = frappe.get_doc("Job Card", {"work_order": order.name, "operation_id": order.operations[0].name, "report_request_id": ["is", "not set"]})
        plan.for_quantity = 1
        plan.save()
        a["base_plan"] = plan.name
        a["drafts"] = []
        for _ in range(9):
            draft = frappe.copy_doc(plan, ignore_no_copy=False)
            draft.for_quantity = 0.1
            draft.insert()
            assert not draft.time_logs and not draft.report_request_id
            a["drafts"].append(draft.name)
        # The tenth empty draft must come from the real native browser Duplicate action.
        a["cards_before_ui"] = frappe.get_all("Job Card", filters={"work_order": order.name}, pluck="name")
        f.write_text(json.dumps(a, ensure_ascii=False, indent=2))
        frappe.db.commit()
        print(json.dumps({"reports": 2, "original_cancelled": True, "replacement_linked": True, "cancelled_quality_history": 1,
            "private_png": 1, "new_blank_drafts": 9, "native_correction": True, "no_old_role_changes": True}))
    elif mode == "checkpoint":
        target = p / "b09-lifecycle-protected-before.json"
        assert not target.exists()
        current = set(frappe.get_all("Job Card", filters={"work_order": a["order"]}, pluck="name"))
        added = current - set(a["cards_before_ui"])
        assert len(added) == 1, "Exactly one browser-created draft required"
        draft = frappe.get_doc("Job Card", added.pop())
        assert draft.owner == a["actors"]["editor"]["user"] and draft.docstatus == 0
        assert not draft.report_request_id and not draft.time_logs
        assert not any(draft.get(k) for k in ("total_completed_qty", "process_loss_qty", "total_time_in_mins", "actual_start_date", "actual_end_date", "job_started", "started_time", "current_time"))
        a["drafts"].append(draft.name)
        a["targets"] = a["drafts"] + [a["report"]]
        assert len(set(a["targets"])) == 11
        frappe.set_user(a["actors"]["reporter"]["user"])
        assert "System Manager" not in frappe.get_roles()
        for name in a["targets"]:
            doc = frappe.get_doc("Job Card", name)
            assert doc.docstatus in (0, 2) and doc.has_permission("delete")
        assert frappe.get_doc("File", a["image_file"]).has_permission("read")
        target.write_text(json.dumps(protected(), ensure_ascii=False, indent=2))
        f.write_text(json.dumps(a, ensure_ascii=False, indent=2))
        print(json.dumps({"browser_duplicate_saved": True, "eleven_unique_targets": True,
            "ordinary_delete_permission_positive": True, "protected_snapshot_saved": True}))
    elif mode == "rotate-editor-password":
        # Invalidate the synthetic browser password after local tool-output handling.
        import secrets
        from frappe.utils.password import update_password
        password = secrets.token_urlsafe(32)
        update_password(a["actors"]["editor"]["user"], password, logout_all_sessions=True)
        a["actors"]["editor"]["password"] = password
        f.write_text(json.dumps(a, ensure_ascii=False, indent=2))
        frappe.db.commit()
        print(json.dumps({"fixture_editor_password_rotated": True, "sessions_invalidated": True, "secrets_printed": False}))
    elif mode == "audit":
        before = json.loads((p / "b09-lifecycle-protected-before.json").read_text())
        assert protected() == before, "Protected rows or image changed"
        assert not frappe.db.exists("Job Card", {"name": ["in", a["drafts"]]})
        assert frappe.db.exists("Job Card", a["report"])
        old = json.loads((p / "b09-lifecycle-before.json").read_text())
        additions = {}
        for dt, base in old.items():
            current = {r.name: hashlib.sha256(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
                for r in frappe.get_all(dt, fields=base["columns"], limit_page_length=0)}
            changed = [name for name, digest in base["rows"].items() if current.get(name) != digest]
            assert not changed, (dt, changed)
            additions[dt] = len(set(current) - set(base["rows"]))
        order = frappe.get_doc("Work Order", a["order"])
        assert (order.operations[0].completed_qty, order.operations[0].process_loss_qty) == (1, 0)
        assert frappe.db.count("Job Card", {"work_order": order.name}) == 5
        assert not frappe.db.exists("Stock Entry", {"work_order": order.name})
        print(json.dumps({"old_tables_unchanged": len(old), "new_rows": additions, "deleted_blank_drafts": 10,
            "original_and_replacement_full_rows_unchanged": True, "time_logs_quality_file_and_binary_unchanged": True,
            "parent_and_operations_unchanged": True, "net_good": 1, "net_bad": 0, "inventory": 0}))
    else:
        raise ValueError("Unsupported mode")
finally:
    frappe.db.rollback()
    frappe.destroy()
