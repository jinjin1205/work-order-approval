"""Read remote content back and verify the exact public allowlist, not runtime data."""
import datetime, hashlib, json, subprocess
from pathlib import Path
root=Path(__file__).resolve().parent.parent
public=root/'.publication/work-order-approval'
sha=subprocess.check_output(['git','-C',str(public),'rev-parse','HEAD'],text=True).strip()
url=subprocess.check_output(['git','-C',str(public),'remote','get-url','origin'],text=True).strip()
assert url=='https://github.com/jinjin1205/work-order-approval.git'
remote=subprocess.check_output(['git','-C',str(public),'ls-remote','origin','refs/heads/main'],text=True).split()[0]
assert remote==sha
verify=root/('.publication/verify-b08-'+sha[:7]);assert not verify.exists()
subprocess.run(['git','clone','--quiet','--depth=1','--branch','main',url,str(verify)],check=True)
assert subprocess.check_output(['git','-C',str(verify),'rev-parse','HEAD'],text=True).strip()==sha
manifest=json.loads((verify/'publication/files.sha256.json').read_text())['files']
actual=set(subprocess.check_output(['git','-C',str(verify),'ls-files','-z']).decode().split('\0'))-{''}
assert actual==set(manifest)|{'publication/files.sha256.json'}
for name,h in manifest.items():
    assert hashlib.sha256((verify/name).read_bytes()).hexdigest()==h,name
    assert (verify/name).read_bytes()==(public/name).read_bytes(),name
assert (verify/'publication/files.sha256.json').read_bytes()==(public/'publication/files.sha256.json').read_bytes()
lock=json.loads((verify/'source/source-lock.json').read_text())
for name,h in lock['files'].items():
    assert hashlib.sha256((root/'.development/repos/erpnext'/name).read_bytes()).hexdigest()==h['modified_sha256'],name
receipt=dict(verified_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),repository=url,branch='main',verified_commit=sha,method=f"Fresh remote clone; remote ref, exact git tracked allowlist and all SHA256 values; {len(lock['files'])} source files compared with local implementation",tracked_files=len(actual),content_hashes_verified=len(manifest),manifest_self_verified_via_git_commit=True,source_files_exact=len(lock['files']),source_patch_sha256=lock['patch_sha256'],missing_or_extra_files=0,hash_mismatches=0,scope='Public code/cards/sanitized evidence only; credentials, raw runtime test data and screenshots excluded. No CI, customer or full-card acceptance claim.')
path=root/('evidence/发布/'+datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')+'-'+sha[:7]+'-remote.json')
path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
