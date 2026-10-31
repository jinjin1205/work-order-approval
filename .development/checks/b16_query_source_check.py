"""Verify the exact B16 runtime manifest; never substitute disk hashes for browser acceptance."""
import hashlib,json,py_compile
from pathlib import Path
manifest=json.loads(Path('/b01/b16-query-source-manifest.json').read_text())
root=Path('/home/frappe/frappe-bench/apps/erpnext')
for name,expected in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    if name.endswith('.py'):py_compile.compile(str(root/name),doraise=True)
print(json.dumps({'runtime_files_match':len(manifest['files']),'python_compiled':sum(n.endswith('.py') for n in manifest['files']),'patch_sha256':manifest['patch_sha256']}))
