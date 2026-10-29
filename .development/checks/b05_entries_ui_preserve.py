"""Read back this package's new records and the complete captured old-row set."""
import hashlib
import json
import os
from pathlib import Path
import frappe

os.chdir("sites")
p = Path("/tmp/b08-private")
a = json.loads((p / "b05-entries-ui.json").read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    frappe.set_user("Administrator")
    baseline = json.loads((p / "b05-entries-before.json").read_text())
    mismatches, additions, seen_changes = [], {}, 0
    for dt, old in baseline.items():
        rows = frappe.get_all(dt, fields=old["columns"], limit_page_length=0)
        current = {r.name: hashlib.sha256(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest() for r in rows}
        for row in rows:
            if row.name not in old["rows"] or current[row.name] == old["rows"][row.name]:
                continue
            if dt == "Work Order" and row.name == a["copy_source"]:
                # Native add_seen appends the actual reader without changing modified.
                # Preserve that audit; prove the entire remaining row equals the old hash.
                seen = json.loads(row["_seen"])
                reader = a["actors"]["initiator"]["user"]
                assert reader in seen
                normalized = dict(row)
                normalized["_seen"] = json.dumps([u for u in seen if u != reader])
                digest = hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
                if digest == old["rows"][row.name]:
                    seen_changes += 1
                    continue
            mismatches.append(dt)
        assert all(name in current for name in old["rows"]), dt + " lost an old row"
        additions[dt] = len(set(current) - set(old["rows"]))
    assert not mismatches, mismatches
    assert seen_changes == 1
    assert additions["Work Order"] == 2
    ready = frappe.get_doc("Work Order", a["ready_order"])
    assert ready.docstatus == 2 and ready.workflow_state == "已取消" and ready.status == "Cancelled"
    assert ready.qty == 10 and ready.produced_qty == 0
    assert not ready.actual_start_date and not ready.actual_end_date
    assert len(ready.operations) == 3 and len(ready.required_items) == 1
    names = frappe.get_all("Work Order", filters={"amended_from": ready.name}, pluck="name")
    assert len(names) == 1
    amended = frappe.get_doc("Work Order", names[0])
    assert amended.name != ready.name and amended.docstatus == 0
    assert amended.workflow_state == "草稿" and amended.status == "Draft" and amended.qty == 10
    assert amended.approval_requested_by == a["actors"]["initiator"]["user"] and not amended.approval_reviewed_by
    assert not amended.operations and not amended.required_items
    assert not amended.actual_start_date and not amended.actual_end_date and not amended.produced_qty
    assert frappe.db.count("Work Order", {"owner": a["actors"]["initiator"]["user"]}) == 2
    assert not frappe.db.exists("Job Card", {"work_order": amended.name})
    cards = frappe.get_all("Job Card", filters={"work_order": ready.name}, fields=["name", "docstatus", "total_completed_qty", "process_loss_qty", "started_time"])
    assert len(cards) == 3 and all(c.docstatus == 0 and not c.total_completed_qty and not c.process_loss_qty and not c.started_time for c in cards)
    assert not frappe.db.exists("Job Card Time Log", {"parent": ["in", [c.name for c in cards]]})
    assert additions["Job Card"] == 3 and additions["Job Card Time Log"] == 0
    assert additions["Stock Entry"] == 0 and additions["Stock Entry Detail"] == 0 and additions["Stock Ledger Entry"] == 0
    assert additions["User"] == 2 and additions["Role"] == 2
    messages = frappe.get_all("Comment", filters={"reference_doctype": "Work Order", "reference_name": ready.name, "comment_type": "Comment"}, fields=["content", "owner"])
    assert any("停止执行" in r.content and "需求调整" in r.content for r in messages)
    assert any("取消修订" in r.content and "无执行事实" in r.content for r in messages)
    print(json.dumps({"old_tables_business_preserved": len(baseline), "raw_old_row_differences": seen_changes,
        "native_seen_reader_additions": seen_changes, "old_business_field_mismatches": 0,
        "new_orders_remaining": 2, "ready_cancelled_with_reason_and_history": True,
        "amended_draft_new_number": True, "amended_source_link_preserved": True,
        "amended_operations": 0, "amended_materials": 0, "amended_new_requester": True,
        "old_approvals_not_inherited": True, "actual_dates_or_quantities_inherited": False,
        "created_empty_copy_deleted": True, "new_draft_job_cards": 3, "new_effective_reports": 0,
        "new_time_logs": 0, "new_stock_entries": 0, "new_stock_ledger_entries": 0,
        "new_users": 2, "new_roles": 2, "old_users_roles_permissions_preserved": True}, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
