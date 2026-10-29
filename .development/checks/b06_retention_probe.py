"""One native same-status write, fully rolled back; not historical reconstruction."""
import hashlib
import json
import os
from pathlib import Path
import frappe

os.chdir("sites")
p = Path("/tmp/b08-private")
a = json.loads((p / "b06-tasks-ui.json").read_text())
baseline = json.loads((p / "b06-tasks-before.json").read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    assert a["site"] == "xgd-b08-http.localhost" and frappe.conf.b08_http_only
    def snapshot():
        return {dt: hashlib.sha256(frappe.as_json(frappe.get_all(dt, fields=old["columns"], order_by="name", limit_page_length=0)).encode()).hexdigest() for dt, old in baseline.items()}
    before = snapshot()
    names = frappe.get_all("Job Card", filters={"work_order": a["order"], "docstatus": 1}, pluck="name")
    assert len(names) == 1
    card = frappe.get_doc("Job Card", names[0])
    columns = baseline["Workstation"]["columns"]
    original = dict(frappe.db.get_value("Workstation", card.workstation, columns, as_dict=True))
    frappe.db.savepoint("b06_station_probe")
    try:
        frappe.set_user(a["actors"]["reporter"]["user"])
        card.update_status_in_workstation(original["status"])
        changed = dict(frappe.db.get_value("Workstation", card.workstation, columns, as_dict=True))
        fields = sorted(key for key in columns if original[key] != changed[key])
        assert fields and set(fields) <= {"status", "modified", "modified_by"}
    finally:
        frappe.db.rollback(save_point="b06_station_probe")
    assert snapshot() == before
    print(json.dumps({"native_same_status_write_changed_fields": fields, "old_tables_restored_after_rollback": len(before),
        "historical_original_field_diff_reconstructed": False, "new_fact_created": False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
