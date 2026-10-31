import hashlib
import json
import py_compile
from pathlib import Path

manifest=json.loads(Path('/b01/a02-source-manifest.json').read_text())
root=Path('/home/frappe/frappe-bench/apps/erpnext')
for name,expected in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    if name.endswith('.py'):py_compile.compile(str(root/name),doraise=True)
print(json.dumps(dict(runtime_files_match=len(manifest['files']),python_compiled=sum(n.endswith('.py')for n in manifest['files']),
    tracked_patch_sha256=manifest['tracked_patch_sha256'],a02_delta_sha256=manifest['a02_delta_sha256'])))
