import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import erpnext
import frappe

manifest = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else "/b01/source-manifest.json").read_text())
root = Path(erpnext.__file__).resolve().parent.parent
actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in manifest["files"]}
assert actual == manifest["files"], "Runtime files do not match checkout manifest"
modules = ["erpnext.manufacturing.doctype.work_order.work_order", "erpnext.manufacturing.doctype.job_card.job_card", "erpnext.stock.doctype.stock_entry.stock_entry"]
origins = {name: importlib.util.find_spec(name).origin for name in modules}
assert all(Path(path).is_relative_to(root) for path in origins.values())
print(json.dumps({"checkout_commit": manifest["commit"], "patch_sha256": manifest.get("patch_sha256"), "erpnext_version": erpnext.__version__, "frappe_version": frappe.__version__, "runtime_root": str(root), "resolved_modules": origins, "files_match": True, "checked_files": actual, "limit": "Only the listed source/metadata files are verified; this is not a full-image audit or business acceptance"}, ensure_ascii=False, indent=2))
