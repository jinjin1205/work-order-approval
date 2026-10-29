"""Read-only source/runtime check; never substitutes for browser acceptance."""
import hashlib
import json
from pathlib import Path

manifest = json.loads(Path("/b01/b06-tasks-source-manifest.json").read_text())
root = Path("/home/frappe/frappe-bench/apps/erpnext")
bad = [name for name, expected in manifest["files"].items() if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected]
assert not bad, bad
python_files = [root / name for name in manifest["files"] if name.endswith(".py")]
for file in python_files:
    compile(file.read_bytes(), str(file), "exec")
print(json.dumps({"files_matched": len(manifest["files"]), "python_compiled": len(python_files),
    "patch_sha256": manifest["patch_sha256"], "mismatches": []}))
