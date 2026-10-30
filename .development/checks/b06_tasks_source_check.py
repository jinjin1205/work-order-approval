"""Read-only source/runtime check; never substitutes for browser acceptance."""
import hashlib
import json
import sys
from pathlib import Path

path = sys.argv[1] if len(sys.argv) > 1 else "/b01/b06-tasks-source-manifest.json"
assert path in ("/b01/b06-tasks-source-manifest.json", "/b01/b07-materials-source-manifest.json", "/b01/b08-navigation-source-manifest.json", "/b01/b08-quality-source-manifest.json", "/b01/b09-lifecycle-source-manifest.json")
manifest = json.loads(Path(path).read_text())
root = Path("/home/frappe/frappe-bench/apps/erpnext")
bad = [name for name, expected in manifest["files"].items() if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected]
assert not bad, bad
python_files = [root / name for name in manifest["files"] if name.endswith(".py")]
for file in python_files:
    compile(file.read_bytes(), str(file), "exec")
print(json.dumps({"files_matched": len(manifest["files"]), "python_compiled": len(python_files),
    "patch_sha256": manifest["patch_sha256"], "mismatches": []}))
