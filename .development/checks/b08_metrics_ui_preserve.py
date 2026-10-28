"""Read only: compare every pre-existing row/column against the captured UI baseline."""
import hashlib
import json
import os
from pathlib import Path

import frappe

os.chdir("sites")
baseline = json.loads(Path("/tmp/b08-private/metrics-20261028-before.json").read_text())
assert baseline["site"] == "xgd-b08-http.localhost"
frappe.init(site=baseline["site"])
frappe.connect()
try:
    assert frappe.conf.b08_http_only
    tables = {}
    for doctype, old in baseline["tables"].items():
        rows = frappe.get_all(doctype, fields=old["columns"], order_by="name", limit_page_length=0)
        current = {
            row.name: hashlib.sha256(json.dumps(
                dict(row), sort_keys=True, ensure_ascii=False, default=str,
                separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
            for row in rows
        }
        missing = len(set(old["rows"]) - set(current))
        changed = sum(current.get(name) != digest for name, digest in old["rows"].items()
                      if name in current)
        tables[doctype] = {
            "old_rows": old["count"], "missing_old_rows": missing,
            "changed_old_rows": changed, "new_rows": len(set(current) - set(old["rows"])),
            "captured_columns": len(old["columns"]),
        }
        assert missing == changed == 0, doctype
    for doctype in ("Stock Entry", "Stock Entry Detail", "Stock Ledger Entry"):
        assert tables[doctype]["new_rows"] == 0, doctype
    print(json.dumps({
        "test_kind": "read-only comparison of all captured rows and columns on the retained synthetic UI site",
        "old_rows_unchanged": True, "tables": tables,
        "no_new_inventory_rows": True,
        "limits": "11 listed business tables only; new synthetic fixture/report rows retained. Not a whole-database or customer-data audit.",
    }, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
