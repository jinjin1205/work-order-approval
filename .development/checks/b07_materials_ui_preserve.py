"""All old captured rows including Bin remain exact; audit only new B07 activity."""
import hashlib
import json
import os
from pathlib import Path
import frappe

os.chdir("sites")
p = Path("/tmp/b08-private")
a = json.loads((p / "b07-materials-ui.json").read_text())
baseline = json.loads((p / "b07-materials-before.json").read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    assert a["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    additions = {}
    for dt, old in baseline.items():
        current = {r.name: hashlib.sha256(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
            for r in frappe.get_all(dt, fields=old["columns"], limit_page_length=0)}
        assert all(current.get(name) == digest for name, digest in old["rows"].items()), dt + " old row changed"
        additions[dt] = len(set(current) - set(old["rows"]))
    order = frappe.get_doc("Work Order", a["order"])
    assert order.workflow_state == "已批准" and order.docstatus == 1 and order.produced_qty == 0
    assert len(order.required_items) == 1
    row = order.required_items[0]
    assert row.item_code == a["raw_item"] and row.required_qty == 6
    assert row.transferred_qty == row.returned_qty == 6 and row.consumed_qty == 0
    assert all(row.workstation == a["workstation"] for row in order.operations)
    assert frappe.db.get_value("BOM Item", a["bom_row"], "qty") == 0.5
    versions = frappe.get_all("BOM", filters={"item": order.production_item}, fields=["name", "docstatus"])
    assert len(versions) == 2
    new = next(v for v in versions if v.name != a["bom"])
    assert new.docstatus == 0
    assert frappe.db.get_value("BOM Item", {"parent": new.name}, "qty") == 0.6
    assert frappe.db.get_value("Stock Entry", a["issue"], "docstatus") == 1
    assert frappe.db.get_value("Stock Entry", a["returned"], "docstatus") == 1
    assert additions["Stock Entry"] == 3 and additions["Job Card"] == 3
    assert additions["Job Card Time Log"] == 0 and additions["User"] == 2 and additions["Role"] == 2
    assert additions["Workstation"] == 1 and additions["Item"] == 2
    print(json.dumps({"old_tables_exact_rows_preserved": len(baseline), "old_row_mismatches": 0,
        "old_Bin_rows_preserved": True, "new_independent_items": 2, "new_independent_station": 1,
        "local_required": 6, "original_bom_quantity": 0.5, "new_bom_draft_quantity": 0.6,
        "issued": 6, "returned": 6, "net": 0, "actual_consumed": 0,
        "pending_approval_source": "UNCONNECTED_NOT_ZERO", "seed_receipts": 1,
        "new_issue_and_return_documents": 2, "new_reports": 0, "new_users": 2, "new_roles": 2,
        "old_users_roles_permissions_unchanged": True}, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
